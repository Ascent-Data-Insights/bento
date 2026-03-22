from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from backend.solver.modules import REGISTRY

router = APIRouter(prefix="/api/v1", tags=["modules"])


class ModuleMetadataResponse(BaseModel):
    key: str
    name: str
    description: str
    dependencies: list[str]
    conflicts: list[str]
    required_dimensions: dict[str, list[str]]
    implemented: bool


@router.get("/modules", response_model=list[ModuleMetadataResponse])
def list_modules() -> list[ModuleMetadataResponse]:
    """Return metadata for all registered constraint modules."""
    result: list[ModuleMetadataResponse] = []
    for key, module_instance in REGISTRY.items():
        meta = module_instance.get_metadata()
        implemented = module_instance.implemented
        result.append(
            ModuleMetadataResponse(
                key=key,
                name=meta.name,
                description=meta.description,
                dependencies=meta.dependencies,
                conflicts=meta.conflicts,
                required_dimensions=meta.required_dimensions,
                implemented=implemented,
            )
        )
    return result
