from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from backend.schemas.profile import DimensionSelections, ModuleConfig, ProfileResponse
from backend.schemas.tenant import TenantResponse


class OnboardRequest(BaseModel):
    tenant_name: str
    industry: str
    profile_name: str
    dimensions: DimensionSelections
    objective: dict[str, float] = Field(..., min_length=1)
    modules: list[ModuleConfig] = []


class OnboardResponse(BaseModel):
    tenant: TenantResponse
    profile: ProfileResponse
