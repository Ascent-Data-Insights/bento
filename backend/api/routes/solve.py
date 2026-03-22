"""Solve endpoint — accepts a routing problem and returns optimized routes."""

from __future__ import annotations

import uuid
from datetime import date

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.config import settings
from backend.db import get_db
from backend.db.models import Job as JobDB
from backend.db.models import Location as LocationDB
from backend.db.models import Profile as ProfileDB
from backend.db.models import Resource as ResourceDB
from backend.db.models import Vehicle as VehicleDB
from backend.schemas.profile import ClientProfile
from backend.schemas.solve import SolveRequest, SolveResponse
from backend.solver.assembler import assemble_solve_request
from backend.solver.exceptions import (
    DependencyError,
    InfeasibleError,
    SolverError,
    SolverTimeoutError,
    ValidationError,
)
from backend.solver.orchestrator import Orchestrator


class SolveRequestBody(BaseModel):
    """Combined request body for the solve endpoint."""
    request: SolveRequest
    profile: ClientProfile


router = APIRouter(prefix="/api/v1", tags=["solve"])


@router.post("/solve", response_model=SolveResponse)
def solve(body: SolveRequestBody) -> SolveResponse:
    """Solve a vehicle routing problem.

    Accepts a solve request (locations, vehicles, resources, matrices) and a
    client profile (dimensions, objective, modules). Returns optimized routes.
    """
    try:
        orchestrator = Orchestrator()
        return orchestrator.solve(body.request, body.profile)
    except (ValidationError, DependencyError) as e:
        raise HTTPException(status_code=422, detail={"message": str(e), "errors": e.errors})
    except InfeasibleError as e:
        raise HTTPException(status_code=400, detail={"message": str(e)})
    except SolverTimeoutError as e:
        raise HTTPException(status_code=504, detail={"message": str(e)})
    except SolverError as e:
        raise HTTPException(status_code=500, detail={"message": str(e)})


@router.post("/tenants/{tenant_id}/solve", response_model=SolveResponse)
def solve_from_db(
    tenant_id: uuid.UUID,
    date: date = Query(..., description="Date to solve for (YYYY-MM-DD)"),
    db: Session = Depends(get_db),
) -> SolveResponse:
    """Solve routes using data from the database."""
    # Load active profile
    profile = db.query(ProfileDB).filter(
        ProfileDB.tenant_id == tenant_id,
        ProfileDB.is_active == True,
    ).first()
    if not profile:
        raise HTTPException(status_code=404, detail="No active profile found for tenant")

    # Load jobs for the date
    jobs = db.query(JobDB).filter(
        JobDB.tenant_id == tenant_id,
        JobDB.date == date,
        JobDB.status == "pending",
    ).all()
    if not jobs:
        raise HTTPException(status_code=404, detail=f"No pending jobs found for {date}")

    # Collect all needed location IDs
    job_location_ids = {j.location_id for j in jobs}

    # Load vehicles and their start/end locations
    vehicles = db.query(VehicleDB).filter(
        VehicleDB.tenant_id == tenant_id,
        VehicleDB.is_active == True,
    ).all()
    if not vehicles:
        raise HTTPException(status_code=404, detail="No active vehicles found")

    depot_location_ids: set = set()
    for v in vehicles:
        depot_location_ids.add(v.start_location_id)
        if v.end_location_id:
            depot_location_ids.add(v.end_location_id)

    # Load all needed locations
    all_location_ids = job_location_ids | depot_location_ids
    locations = db.query(LocationDB).filter(
        LocationDB.id.in_(all_location_ids),
        LocationDB.tenant_id == tenant_id,
    ).all()

    # Load active resources
    resources = db.query(ResourceDB).filter(
        ResourceDB.tenant_id == tenant_id,
        ResourceDB.is_active == True,
    ).all()

    # Also add pickup/dropoff locations for resources
    resource_location_ids: set = set()
    for r in resources:
        resource_location_ids.add(r.pickup_location_id)
        if r.dropoff_location_id:
            resource_location_ids.add(r.dropoff_location_id)

    missing_loc_ids = resource_location_ids - {loc.id for loc in locations}
    if missing_loc_ids:
        extra_locs = db.query(LocationDB).filter(
            LocationDB.id.in_(missing_loc_ids),
            LocationDB.tenant_id == tenant_id,
        ).all()
        locations.extend(extra_locs)

    # Build location ID map for matrices — use UUID strings directly for guaranteed uniqueness
    loc_id_map = {str(loc.id): str(loc.id) for loc in locations}

    # Compute matrices via OSRM
    coords = ";".join(f"{loc.longitude},{loc.latitude}" for loc in locations)
    osrm_url = f"{settings.osrm_base_url}/table/v1/driving/{coords}"

    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.get(osrm_url, params={"annotations": "distance,duration"})
            response.raise_for_status()
            data = response.json()
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"OSRM request failed: {e}")

    if data.get("code") != "Ok":
        raise HTTPException(status_code=502, detail=f"OSRM error: {data.get('code')}")

    # Build matrices with string IDs
    loc_list = list(locations)
    distance_matrix: dict[str, dict[str, float]] = {}
    time_matrix: dict[str, dict[str, float]] = {}
    for i, from_loc in enumerate(loc_list):
        from_id = loc_id_map[str(from_loc.id)]
        distance_matrix[from_id] = {}
        time_matrix[from_id] = {}
        for j, to_loc in enumerate(loc_list):
            to_id = loc_id_map[str(to_loc.id)]
            dist_raw = data["distances"][i][j]
            dur_raw = data["durations"][i][j]
            if dist_raw is None or dur_raw is None:
                raise HTTPException(
                    status_code=502,
                    detail=f"OSRM: no route between {from_id} and {to_id}",
                )
            distance_matrix[from_id][to_id] = round(dist_raw / 1609.34, 1)
            time_matrix[from_id][to_id] = round(dur_raw / 60, 1)

    matrices = {"distance": distance_matrix, "time": time_matrix}

    # Assemble and solve
    try:
        solve_request, client_profile = assemble_solve_request(
            profile, jobs, locations, vehicles, resources, matrices
        )
        orchestrator = Orchestrator()
        return orchestrator.solve(solve_request, client_profile)
    except (ValidationError, DependencyError) as e:
        raise HTTPException(status_code=422, detail={"message": str(e), "errors": e.errors})
    except InfeasibleError as e:
        raise HTTPException(status_code=400, detail={"message": str(e)})
    except SolverTimeoutError as e:
        raise HTTPException(status_code=504, detail={"message": str(e)})
    except SolverError as e:
        raise HTTPException(status_code=500, detail={"message": str(e)})
