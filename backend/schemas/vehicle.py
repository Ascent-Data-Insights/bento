from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel


class VehicleCreate(BaseModel):
    name: str
    start_location_id: uuid.UUID
    end_location_id: uuid.UUID | None = None
    compartments: list[dict[str, Any]]
    external_id: str | None = None


class VehicleResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    start_location_id: uuid.UUID
    end_location_id: uuid.UUID | None
    compartments: list[dict[str, Any]]
    is_active: bool
    external_id: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
