from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.db import get_db
from backend.db.models import Profile, Tenant
from backend.schemas.onboard import OnboardRequest, OnboardResponse
from backend.schemas.profile import ProfileResponse
from backend.schemas.tenant import TenantResponse

router = APIRouter(prefix="/api/v1", tags=["onboard"])


@router.post("/tenants/onboard", response_model=OnboardResponse, status_code=201)
def onboard_tenant(body: OnboardRequest, db: Session = Depends(get_db)) -> OnboardResponse:
    """Create a tenant and its first profile in a single transaction."""
    tenant = Tenant(name=body.tenant_name, industry=body.industry)
    db.add(tenant)
    db.flush()  # Populate tenant.id without committing

    profile = Profile(
        tenant_id=tenant.id,
        name=body.profile_name,
        origin_model=body.dimensions.origin_model.value,
        fleet_composition=body.dimensions.fleet_composition.value,
        objective=body.objective,
        modules=[m.model_dump() for m in body.modules],
    )
    db.add(profile)
    db.commit()
    db.refresh(tenant)
    db.refresh(profile)

    return OnboardResponse(
        tenant=TenantResponse.model_validate(tenant),
        profile=ProfileResponse.model_validate(profile),
    )
