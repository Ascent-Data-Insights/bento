#!/usr/bin/env bash
set -e

# --- Config ---
ENV_FILE="${1:-/root/bento/.env.production}"

# --- Load env vars ---
set -a
source "$ENV_FILE"
set +a

# --- Parse DATABASE_URL via Python ---
read -r DB_USER DB_PASS DB_HOST DB_PORT DB_NAME < <(
    ROUTING_DATABASE_URL="$ROUTING_DATABASE_URL" python3 -c "
import os
from urllib.parse import urlparse
u = urlparse(os.environ['ROUTING_DATABASE_URL'])
print(u.username, u.password, u.hostname, u.port, u.path.lstrip('/'))
"
)

[[ -n "$DB_NAME" && -n "$DB_USER" && -n "$DB_HOST" ]] || { echo "ERROR: failed to parse ROUTING_DATABASE_URL"; exit 1; }

# --- Derive project dir from env file location ---
PROJECT_DIR="$(dirname "$(realpath "$ENV_FILE")")"

# --- Warn user if script fails while service is stopped ---
trap 'echo "ERROR: reseed failed. bento-api is still stopped. Restart manually with: systemctl start bento-api"; exit 1' ERR

# --- Stop service ---
echo "Stopping bento-api..."
systemctl stop bento-api

# --- Recreate database ---
echo "Recreating database $DB_NAME..."
sudo -u postgres psql \
    --variable="dbname=$DB_NAME" \
    --variable="dbuser=$DB_USER" \
    -v ON_ERROR_STOP=1 \
    <<'SQL'
SELECT pg_terminate_backend(pid)
  FROM pg_stat_activity
  WHERE datname = :'dbname' AND pid <> pg_backend_pid();
DROP DATABASE IF EXISTS :"dbname";
CREATE DATABASE :"dbname";
GRANT ALL PRIVILEGES ON DATABASE :"dbname" TO :"dbuser";
\connect :"dbname"
GRANT ALL ON SCHEMA public TO :"dbuser";
SQL

# --- Run migrations ---
echo "Running migrations..."
cd "$PROJECT_DIR"
uv run alembic upgrade head

# --- Seed data ---
echo "Seeding database..."
uv run python -m backend.db.seed

# --- Restart service ---
echo "Restarting bento-api..."
systemctl start bento-api

# --- Clear ERR trap now that service is back up ---
trap - ERR

echo "Reseed complete."
