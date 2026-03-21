"""Solve endpoint — accepts a routing problem and returns optimized routes."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from pydantic import BaseModel

from backend.schemas.solve import SolveRequest, SolveResponse
from backend.schemas.profile import ClientProfile
from backend.solver.orchestrator import Orchestrator
from backend.solver.exceptions import (
    DependencyError,
    InfeasibleError,
    SolverError,
    SolverTimeoutError,
    ValidationError,
)


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
