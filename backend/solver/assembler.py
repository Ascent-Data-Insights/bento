"""Assemble a SolveRequest from database records."""

from __future__ import annotations

from backend.db.models import (
    Job as JobDB,
    Location as LocationDB,
    Profile as ProfileDB,
    Resource as ResourceDB,
    Vehicle as VehicleDB,
)
from backend.schemas.profile import ClientProfile, DimensionSelections, ModuleConfig
from backend.schemas.solve import SolveRequest


def assemble_solve_request(
    profile: ProfileDB,
    jobs: list[JobDB],
    locations: list[LocationDB],
    vehicles: list[VehicleDB],
    resources: list[ResourceDB],
    matrices: dict[str, dict[str, dict[str, float]]],
) -> tuple[SolveRequest, ClientProfile]:
    """Transform DB records into solver-ready SolveRequest and ClientProfile."""

    # Build location ID mapping (DB UUID -> solver string ID)
    # Use UUID strings directly for guaranteed uniqueness
    loc_id_map: dict[str, str] = {str(loc.id): str(loc.id) for loc in locations}

    # Build solver locations from jobs + their locations
    # Jobs override location service_time and required_resources
    # Group jobs by location to handle multiple jobs per location explicitly
    jobs_by_location: dict[str, list[JobDB]] = {}
    for job in jobs:
        key = str(job.location_id)
        jobs_by_location.setdefault(key, []).append(job)

    # For now, take the first job per location (warn if multiples exist)
    job_by_location: dict[str, JobDB] = {}
    for loc_key, loc_jobs in jobs_by_location.items():
        job_by_location[loc_key] = loc_jobs[0]

    solver_locations = []
    for loc in locations:
        loc_str_id = loc_id_map[str(loc.id)]
        job = job_by_location.get(str(loc.id))

        solver_locations.append({
            "id": loc_str_id,
            "latitude": loc.latitude,
            "longitude": loc.longitude,
            "service_time": job.service_time if job else loc.service_time,
            "required_resources": job.required_resources if job else loc.required_resources,
        })

    # Build solver vehicles
    solver_vehicles = []
    for v in vehicles:
        solver_vehicles.append({
            "id": str(v.id),
            "start_location_id": loc_id_map[str(v.start_location_id)],
            "end_location_id": loc_id_map[str(v.end_location_id)] if v.end_location_id else None,
            "compartments": v.compartments,
        })

    # Build solver resources
    solver_resources = []
    for r in resources:
        resource_data: dict = {
            "id": str(r.id),
            "pickup_location_id": loc_id_map[str(r.pickup_location_id)],
            "compartment_types": r.compartment_types,
            "capacity_consumption": r.capacity_consumption,
            "quantity": r.quantity,
            "stays_with_vehicle": r.stays_with_vehicle,
            "attributes": r.attributes,
        }
        if r.dropoff_location_id:
            resource_data["dropoff_location_id"] = loc_id_map[str(r.dropoff_location_id)]
        solver_resources.append(resource_data)

    # Build module_data from jobs (time windows)
    module_data: dict = {}

    # Check if time_windows module is enabled
    tw_enabled = any(
        m.get("key") == "time_windows" and m.get("enabled", True)
        for m in (profile.modules or [])
    )
    if tw_enabled:
        windows = []
        for job in job_by_location.values():
            if job.time_window_earliest is not None and job.time_window_latest is not None:
                loc_str_id = loc_id_map[str(job.location_id)]
                windows.append({
                    "location_id": loc_str_id,
                    "earliest": job.time_window_earliest,
                    "latest": job.time_window_latest,
                })
        if windows:
            module_data["time_windows"] = {"windows": windows}

    # Check if co_delivery is enabled
    cd_enabled = any(
        m.get("key") == "co_delivery" and m.get("enabled", True)
        for m in (profile.modules or [])
    )
    if cd_enabled:
        # Empty locations list = apply co-delivery to all locations with required_resources
        module_data["co_delivery"] = {"locations": []}

    # Remap matrices to use string IDs (matrices are already keyed by string IDs)
    remapped_matrices: dict[str, dict[str, dict[str, float]]] = {}
    for matrix_name, matrix in matrices.items():
        remapped: dict[str, dict[str, float]] = {}
        for from_id, row in matrix.items():
            remapped[from_id] = {}
            for to_id, value in row.items():
                remapped[from_id][to_id] = value
        remapped_matrices[matrix_name] = remapped

    # Build SolveRequest
    solve_request = SolveRequest(
        locations=solver_locations,
        vehicles=solver_vehicles,
        resources=solver_resources,
        matrices=remapped_matrices,
        module_data=module_data,
    )

    # Build ClientProfile
    client_profile = ClientProfile(
        tenant_id=str(profile.tenant_id),
        name=profile.name,
        dimensions=DimensionSelections(
            origin_model=profile.origin_model,
            fleet_composition=profile.fleet_composition,
        ),
        objective=profile.objective,
        modules=[
            ModuleConfig(**m) for m in (profile.modules or [])
        ],
    )

    return solve_request, client_profile
