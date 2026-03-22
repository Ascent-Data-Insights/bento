from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.db import get_db
from backend.db.models import Resource, Tenant
from backend.schemas.resource import ResourceCreate, ResourceResponse

router = APIRouter(prefix="/api/v1", tags=["resources"])


@router.post("/tenants/{tenant_id}/resources", response_model=list[ResourceResponse], status_code=201)
def create_resources(
    tenant_id: uuid.UUID,
    body: list[ResourceCreate],
    db: Session = Depends(get_db),
) -> list[Resource]:
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    resources = []
    for r in body:
        resource = Resource(
            tenant_id=tenant_id,
            name=r.name,
            pickup_location_id=r.pickup_location_id,
            dropoff_location_id=r.dropoff_location_id,
            compartment_types=r.compartment_types,
            capacity_consumption=r.capacity_consumption,
            quantity=r.quantity,
            stays_with_vehicle=r.stays_with_vehicle,
            attributes=r.attributes,
            external_id=r.external_id,
        )
        db.add(resource)
        resources.append(resource)
    db.commit()
    for r in resources:
        db.refresh(r)
    return resources


@router.get("/tenants/{tenant_id}/resources", response_model=list[ResourceResponse])
def list_resources(tenant_id: uuid.UUID, db: Session = Depends(get_db)) -> list[Resource]:
    return db.query(Resource).filter(Resource.tenant_id == tenant_id, Resource.is_active == True).all()
