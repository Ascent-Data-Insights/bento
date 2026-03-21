"""FastAPI application entry point."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.routes.solve import router as solve_router

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


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
