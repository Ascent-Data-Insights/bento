from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.db import get_db
from backend.db.models import Location, Tenant
from backend.schemas.location import LocationCreate, LocationResponse

router = APIRouter(prefix="/api/v1", tags=["locations"])


@router.post("/tenants/{tenant_id}/locations", response_model=list[LocationResponse], status_code=201)
def create_locations(
    tenant_id: uuid.UUID,
    body: list[LocationCreate],
    db: Session = Depends(get_db),
) -> list[Location]:
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    locations = []
    for loc in body:
        location = Location(
            tenant_id=tenant_id,
            name=loc.name,
            latitude=loc.latitude,
            longitude=loc.longitude,
            service_time=loc.service_time,
            required_resources=loc.required_resources,
            external_id=loc.external_id,
        )
        db.add(location)
        locations.append(location)
    db.commit()
    for loc in locations:
        db.refresh(loc)
    return locations


@router.get("/tenants/{tenant_id}/locations", response_model=list[LocationResponse])
def list_locations(tenant_id: uuid.UUID, db: Session = Depends(get_db)) -> list[Location]:
    return db.query(Location).filter(Location.tenant_id == tenant_id).all()
