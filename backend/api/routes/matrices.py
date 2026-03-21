"""Matrix computation endpoint — computes distance/time matrices via OSRM."""

from __future__ import annotations

import hashlib
import json
import time as time_module
from typing import Any

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.config import settings

router = APIRouter(prefix="/api/v1", tags=["matrices"])


class MatrixLocation(BaseModel):
    id: str
    latitude: float
    longitude: float


class MatrixRequest(BaseModel):
    locations: list[MatrixLocation]


class MatrixResponse(BaseModel):
    matrices: dict[str, dict[str, dict[str, float]]]
    cached: bool = False


# In-memory cache: cache_key -> (matrices, timestamp)
_cache: dict[str, tuple[dict[str, dict[str, dict[str, float]]], float]] = {}
CACHE_TTL = 3600  # 1 hour


def _cache_key(locations: list[MatrixLocation]) -> str:
    """Generate a cache key from sorted location coordinates."""
    # Sort by ID for deterministic key regardless of input order
    coords = sorted([(loc.id, loc.latitude, loc.longitude) for loc in locations])
    return hashlib.md5(json.dumps(coords).encode()).hexdigest()


def _get_cached(key: str) -> dict[str, dict[str, dict[str, float]]] | None:
    """Return cached matrices if still valid, else None."""
    if key in _cache:
        matrices, timestamp = _cache[key]
        if time_module.time() - timestamp < CACHE_TTL:
            return matrices
        del _cache[key]
    return None


def _set_cached(key: str, matrices: dict[str, dict[str, dict[str, float]]]) -> None:
    _cache[key] = (matrices, time_module.time())


@router.post("/matrices", response_model=MatrixResponse)
async def compute_matrices(request: MatrixRequest) -> MatrixResponse:
    """Compute NxN distance and time matrices for a list of locations using OSRM."""
    if len(request.locations) < 2:
        raise HTTPException(status_code=422, detail="At least 2 locations required.")

    ids = [loc.id for loc in request.locations]
    if len(ids) != len(set(ids)):
        raise HTTPException(status_code=422, detail="Location IDs must be unique.")

    # Check cache
    key = _cache_key(request.locations)
    cached = _get_cached(key)
    if cached is not None:
        return MatrixResponse(matrices=cached, cached=True)

    # Build OSRM request — coordinates as lon,lat;lon,lat;...
    coords = ";".join(
        f"{loc.longitude},{loc.latitude}" for loc in request.locations
    )
    osrm_url = f"{settings.osrm_base_url}/table/v1/driving/{coords}"
    params = {"annotations": "distance,duration"}

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(osrm_url, params=params)
            response.raise_for_status()
            data = response.json()
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"OSRM request failed: {e}")

    if data.get("code") != "Ok":
        raise HTTPException(
            status_code=502,
            detail=f"OSRM error: {data.get('code', 'unknown')}",
        )

    # Parse response into our matrix format
    distances = data["distances"]  # meters
    durations = data["durations"]  # seconds
    locations = request.locations

    distance_matrix: dict[str, dict[str, float]] = {}
    time_matrix: dict[str, dict[str, float]] = {}

    for i, from_loc in enumerate(locations):
        distance_matrix[from_loc.id] = {}
        time_matrix[from_loc.id] = {}
        for j, to_loc in enumerate(locations):
            dist_raw = distances[i][j]
            dur_raw = durations[i][j]
            if dist_raw is None or dur_raw is None:
                raise HTTPException(
                    status_code=502,
                    detail=f"OSRM returned no route between '{from_loc.id}' and '{to_loc.id}'.",
                )
            # meters -> miles, rounded to 1 decimal
            distance_matrix[from_loc.id][to_loc.id] = round(dist_raw / 1609.34, 1)
            # seconds -> minutes, rounded to 1 decimal
            time_matrix[from_loc.id][to_loc.id] = round(dur_raw / 60, 1)

    matrices = {"distance": distance_matrix, "time": time_matrix}

    # Cache the result
    _set_cached(key, matrices)

    return MatrixResponse(matrices=matrices, cached=False)
