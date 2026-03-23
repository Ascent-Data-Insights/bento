"""FastAPI application entry point."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.config import settings
from backend.api.routes.jobs import router as jobs_router
from backend.api.routes.locations import router as locations_router
from backend.api.routes.matrices import router as matrices_router
from backend.api.routes.modules import router as modules_router
from backend.api.routes.onboard import router as onboard_router
from backend.api.routes.profiles import router as profiles_router
from backend.api.routes.resources import router as resources_router
from backend.api.routes.solve import router as solve_router
from backend.api.routes.tenants import router as tenants_router
from backend.api.routes.vehicles import router as vehicles_router

app = FastAPI(
    title="Routing Product API",
    version="0.1.0",
    description="Modular vehicle routing optimization API.",
)

_cors_origins = (
    ["*"]
    if settings.cors_origins.strip() == "*"
    else [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(solve_router)
app.include_router(matrices_router)
app.include_router(modules_router)
app.include_router(onboard_router)
app.include_router(tenants_router)
app.include_router(profiles_router)
app.include_router(locations_router)
app.include_router(vehicles_router)
app.include_router(resources_router)
app.include_router(jobs_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
