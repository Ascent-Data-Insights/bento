from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from backend.db import get_db
from backend.db.models import Tenant
from backend.schemas.tenant import TenantCreate, TenantResponse

router = APIRouter(prefix="/api/v1", tags=["tenants"])


@router.post("/tenants", response_model=TenantResponse, status_code=201)
def create_tenant(body: TenantCreate, db: Session = Depends(get_db)) -> Tenant:
    tenant = Tenant(name=body.name, industry=body.industry, branding=body.branding)
    db.add(tenant)
    db.commit()
    db.refresh(tenant)
    return tenant


@router.get("/tenants", response_model=list[TenantResponse])
def list_tenants(db: Session = Depends(get_db)) -> list[Tenant]:
    return db.query(Tenant).all()


@router.get("/tenants/{tenant_id}", response_model=TenantResponse)
def get_tenant(tenant_id: uuid.UUID, db: Session = Depends(get_db)) -> Tenant:
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return tenant


@router.delete("/tenants/{tenant_id}", status_code=204)
def delete_tenant(tenant_id: uuid.UUID, db: Session = Depends(get_db)) -> Response:
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    db.delete(tenant)
    db.commit()
    return Response(status_code=204)
