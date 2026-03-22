"""FastAPI application entry point."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.routes.jobs import router as jobs_router
from backend.api.routes.locations import router as locations_router
from backend.api.routes.matrices import router as matrices_router
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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(solve_router)
app.include_router(matrices_router)
app.include_router(tenants_router)
app.include_router(profiles_router)
app.include_router(locations_router)
app.include_router(vehicles_router)
app.include_router(resources_router)
app.include_router(jobs_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
