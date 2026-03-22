from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel


class ResourceCreate(BaseModel):
    name: str
    pickup_location_id: uuid.UUID
    dropoff_location_id: uuid.UUID | None = None
    compartment_types: list[str]
    capacity_consumption: dict[str, float]
    quantity: int = 1
    stays_with_vehicle: bool = False
    attributes: dict[str, Any] = {}
    external_id: str | None = None


class ResourceResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    pickup_location_id: uuid.UUID
    dropoff_location_id: uuid.UUID | None
    compartment_types: list[str]
    capacity_consumption: dict[str, float]
    quantity: int
    stays_with_vehicle: bool
    attributes: dict[str, Any]
    is_active: bool
    external_id: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
