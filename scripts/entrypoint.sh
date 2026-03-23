#!/bin/sh
set -e
uv run alembic upgrade head
if [ "${ROUTING_SKIP_SEED}" != "true" ]; then
    uv run python -m backend.db.seed
fi
exec uv run uvicorn backend.main:app --host 0.0.0.0 --port 8000
