from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel


class LocationCreate(BaseModel):
    name: str
    latitude: float
    longitude: float
    service_time: float = 0.0
    required_resources: list[dict[str, Any]] = []
    external_id: str | None = None


class LocationResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    latitude: float
    longitude: float
    service_time: float
    required_resources: list[dict[str, Any]]
    external_id: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
