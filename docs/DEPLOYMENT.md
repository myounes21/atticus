# Deployment Runbook

## 1) Prepare Environment

From repo root:

1. `cp .env.example .env`
2. Edit `.env` for production:
   - `APP_ENV=production`
   - `APP_DOMAIN=<your-domain>`
   - `ALLOWED_ORIGINS=["https://<your-domain>"]`
   - `JWT_SECRET_KEY=<long-random-secret>`
   - `POSTGRES_PASSWORD=<strong-password>`
   - `DEMO_AUTH=false`
   - `ENABLE_SELF_REGISTER=false`
   - `NEXT_PUBLIC_DEMO_AUTH=false`
   - `NEXT_PUBLIC_ENABLE_SELF_REGISTER=false`
   - optional observability:
     - `LANGFUSE_ENABLED=true`
     - `LANGFUSE_PUBLIC_KEY=<key>`
     - `LANGFUSE_SECRET_KEY=<key>`
     - `LANGFUSE_BASE_URL=https://cloud.langfuse.com`
     - `LANGFUSE_CAPTURE_CONTENT=false`

## 2) Start Application

- Build and run core services:
  - `docker compose up --build -d`
- Verify health:
  - `docker compose ps`
  - `curl -f http://localhost:8000/ready`

## 3) Start HTTPS Proxy

- Ensure DNS points your domain to server IP.
- Start Caddy profile:
  - `docker compose --profile prod up -d caddy`
- Check proxy logs:
  - `docker compose logs -f caddy`

## 4) Seed Demo Data

- Run deterministic reset+seed job:
  - `docker compose --profile demo run --rm demo-seed`

## 5) Smoke Checks

- Open `https://<your-domain>`.
- Login as admin and verify case/document views.
- Login as lawyer and verify case chat responds.
- Validate source references appear in chat messages.

## 6) Operations

- Tail logs:
  - `docker compose logs -f backend frontend celery-worker`
- Restart one service:
  - `docker compose restart backend`
- Full restart:
  - `docker compose down && docker compose up -d`
- Backups profile (optional):
  - `docker compose --profile ops up -d postgres-backup`

## 7) Recovery

- Rebuild and restart:
  - `docker compose down`
  - `docker compose up --build -d`
- Refresh demo state:
  - `docker compose --profile demo run --rm demo-seed`
