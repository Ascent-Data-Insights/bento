from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.db import get_db
from backend.db.models import Profile, Tenant
from backend.schemas.profile import ProfileCreate, ProfileResponse

router = APIRouter(prefix="/api/v1", tags=["profiles"])


@router.post("/tenants/{tenant_id}/profiles", response_model=ProfileResponse, status_code=201)
def create_profile(tenant_id: uuid.UUID, body: ProfileCreate, db: Session = Depends(get_db)) -> Profile:
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    profile = Profile(
        tenant_id=tenant_id,
        name=body.name,
        origin_model=body.dimensions.origin_model.value,
        fleet_composition=body.dimensions.fleet_composition.value,
        objective=body.objective,
        modules=[m.model_dump() for m in body.modules],
    )
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile


@router.get("/tenants/{tenant_id}/profiles", response_model=list[ProfileResponse])
def list_profiles(tenant_id: uuid.UUID, db: Session = Depends(get_db)) -> list[Profile]:
    return db.query(Profile).filter(Profile.tenant_id == tenant_id).all()


@router.get("/tenants/{tenant_id}/profiles/{profile_id}", response_model=ProfileResponse)
def get_profile(tenant_id: uuid.UUID, profile_id: uuid.UUID, db: Session = Depends(get_db)) -> Profile:
    profile = db.query(Profile).filter(
        Profile.id == profile_id,
        Profile.tenant_id == tenant_id,
    ).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile


@router.put("/tenants/{tenant_id}/profiles/{profile_id}", response_model=ProfileResponse)
def update_profile(tenant_id: uuid.UUID, profile_id: uuid.UUID, body: ProfileCreate, db: Session = Depends(get_db)) -> Profile:
    profile = db.query(Profile).filter(
        Profile.id == profile_id,
        Profile.tenant_id == tenant_id,
    ).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    profile.name = body.name
    profile.origin_model = body.dimensions.origin_model.value
    profile.fleet_composition = body.dimensions.fleet_composition.value
    profile.objective = body.objective
    profile.modules = [m.model_dump() for m in body.modules]
    db.commit()
    db.refresh(profile)
    return profile
