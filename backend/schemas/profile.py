from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class OriginModel(str, Enum):
    SINGLE_DEPOT = "single_depot"
    MULTI_DEPOT = "multi_depot"
    DEPOT_INTERMEDIATE = "depot_intermediate"


class FleetComposition(str, Enum):
    HOMOGENEOUS = "homogeneous"
    HETEROGENEOUS = "heterogeneous"


class DimensionSelections(BaseModel):
    origin_model: OriginModel
    fleet_composition: FleetComposition


class ModuleConfig(BaseModel):
    key: str
    enabled: bool = True
    params: dict[str, Any] = {}


class ClientProfile(BaseModel):
    id: str | None = None
    tenant_id: str
    name: str
    dimensions: DimensionSelections
    objective: dict[str, float] = Field(..., min_length=1)
    modules: list[ModuleConfig] = []
