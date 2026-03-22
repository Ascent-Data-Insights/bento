from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any

from pydantic import BaseModel


class JobCreate(BaseModel):
    location_id: uuid.UUID
    date: date
    name: str
    description: str | None = None
    service_time: float = 0.0
    required_resources: list[dict[str, Any]] = []
    time_window_earliest: float | None = None
    time_window_latest: float | None = None
    external_id: str | None = None


class JobResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    location_id: uuid.UUID
    date: date
    name: str
    description: str | None
    service_time: float
    required_resources: list[dict[str, Any]]
    time_window_earliest: float | None
    time_window_latest: float | None
    status: str
    external_id: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
