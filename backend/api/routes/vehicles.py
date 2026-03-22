from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.db import get_db
from backend.db.models import Tenant, Vehicle
from backend.schemas.vehicle import VehicleCreate, VehicleResponse

router = APIRouter(prefix="/api/v1", tags=["vehicles"])


@router.post("/tenants/{tenant_id}/vehicles", response_model=list[VehicleResponse], status_code=201)
def create_vehicles(
    tenant_id: uuid.UUID,
    body: list[VehicleCreate],
    db: Session = Depends(get_db),
) -> list[Vehicle]:
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    vehicles = []
    for v in body:
        vehicle = Vehicle(
            tenant_id=tenant_id,
            name=v.name,
            start_location_id=v.start_location_id,
            end_location_id=v.end_location_id,
            compartments=v.compartments,
            external_id=v.external_id,
        )
        db.add(vehicle)
        vehicles.append(vehicle)
    db.commit()
    for v in vehicles:
        db.refresh(v)
    return vehicles


@router.get("/tenants/{tenant_id}/vehicles", response_model=list[VehicleResponse])
def list_vehicles(tenant_id: uuid.UUID, db: Session = Depends(get_db)) -> list[Vehicle]:
    return db.query(Vehicle).filter(Vehicle.tenant_id == tenant_id, Vehicle.is_active == True).all()
