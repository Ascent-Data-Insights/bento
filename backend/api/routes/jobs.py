from __future__ import annotations

import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.db import get_db
from backend.db.models import Job, Tenant
from backend.schemas.job import JobCreate, JobResponse

router = APIRouter(prefix="/api/v1", tags=["jobs"])


@router.post("/tenants/{tenant_id}/jobs", response_model=list[JobResponse], status_code=201)
def create_jobs(
    tenant_id: uuid.UUID,
    body: list[JobCreate],
    db: Session = Depends(get_db),
) -> list[Job]:
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    jobs = []
    for j in body:
        job = Job(
            tenant_id=tenant_id,
            location_id=j.location_id,
            date=j.date,
            name=j.name,
            description=j.description,
            service_time=j.service_time,
            required_resources=j.required_resources,
            time_window_earliest=j.time_window_earliest,
            time_window_latest=j.time_window_latest,
            external_id=j.external_id,
        )
        db.add(job)
        jobs.append(job)
    db.commit()
    for j in jobs:
        db.refresh(j)
    return jobs


@router.get("/tenants/{tenant_id}/jobs", response_model=list[JobResponse])
def list_jobs(
    tenant_id: uuid.UUID,
    date: date = Query(..., description="Filter jobs by date (YYYY-MM-DD)"),
    db: Session = Depends(get_db),
) -> list[Job]:
    return db.query(Job).filter(Job.tenant_id == tenant_id, Job.date == date).all()
