from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel


class TenantCreate(BaseModel):
    name: str
    industry: str
    branding: dict[str, Any] | None = None


class TenantResponse(BaseModel):
    id: uuid.UUID
    name: str
    industry: str
    branding: dict[str, Any] | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
