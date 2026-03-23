# Production Deployment

## Frontend (Netlify)

1. Connect the repo to Netlify. The build settings are already in `frontend/netlify.toml`.
2. In the Netlify dashboard, go to **Site configuration > Environment variables** and add:
   ```
   VITE_API_URL=https://api.bento.ascentdi.com
   ```
3. Deploy. Netlify picks up the `netlify.toml` automatically — no manual build config needed.
4. Set the custom domain to `bento.ascentdi.com` in **Domain management**.

---

## Backend (Hetzner VM + Caddy)

### First-time setup

1. SSH into the VM.

2. Copy the env template and fill in real values:
   ```sh
   cp .env.production.example .env.production
   nano .env.production
   ```
   At minimum, set `ROUTING_DATABASE_URL` to point at the existing Postgres instance.

3. Create the database if it does not already exist:
   ```sh
   psql -U postgres -c "CREATE DATABASE bento;"
   ```

4. Start the API container (migrations run automatically on startup):
   ```sh
   docker compose -f docker-compose.prod.yml up -d
   ```

5. Add the Caddy block from `deploy/Caddyfile.example` to your Caddyfile (typically `/etc/caddy/Caddyfile`), then reload:
   ```sh
   sudo systemctl reload caddy
   ```
   Caddy handles TLS certificate provisioning automatically.

---

## Common Operations

### View API logs
```sh
docker compose -f docker-compose.prod.yml logs -f api
```

### Redeploy after a code change
```sh
docker compose -f docker-compose.prod.yml build api
docker compose -f docker-compose.prod.yml up -d api
```

### Run migrations manually (without restarting the container)
```sh
docker compose -f docker-compose.prod.yml exec api uv run alembic upgrade head
```

### Stop the API
```sh
docker compose -f docker-compose.prod.yml down
```
