#!/bin/sh
set -e
uv run alembic upgrade head
uv run python -m backend.db.seed
exec uv run uvicorn backend.main:app --host 0.0.0.0 --port 8000
