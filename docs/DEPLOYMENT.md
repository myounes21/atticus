# Deployment Runbook

## 1) Prepare Environment

From repo root:

1. `cp .env.production.example .env`
2. Edit `.env` for production:
   - `APP_ENV=production`
   - `APP_DOMAIN=<your-domain>`
   - `ALLOWED_ORIGINS=["https://<your-domain>"]`
   - `JWT_SECRET_KEY=<long-random-secret>`
   - `POSTGRES_PASSWORD=<strong-password>`
   - `EMBEDDING_BACKEND=sentence_transformers`
   - `EMBEDDER_MODEL=BAAI/bge-m3`
   - `EMBEDDING_FALLBACK_ENABLED=false`
   - `ELASTIC_XPACK_SECURITY_ENABLED=true`
   - `ELASTICSEARCH_PASSWORD=<strong-password>`
   - `DEMO_AUTH=false`
   - `ENABLE_SELF_REGISTER=false`
   - `NEXT_PUBLIC_DEMO_AUTH=false`
   - `NEXT_PUBLIC_ENABLE_SELF_REGISTER=false`
   - required observability:
     - `LANGFUSE_PUBLIC_KEY=<key>`
     - `LANGFUSE_SECRET_KEY=<key>`
     - `LANGFUSE_BASE_URL=https://cloud.langfuse.com`
     - `LANGFUSE_CAPTURE_CONTENT=false`

  For local development, continue using `.env.example`.

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

## 8) CI/CD Setup

This repo includes two workflows:

- CI gate: `.github/workflows/eval_gate.yml`
- CD deploy: `.github/workflows/deploy_cd.yml`

CD deploy behavior:

- Push to `main` auto-deploys to **staging** (if staging secrets are configured).
- Production deploy is **manual only** via GitHub Actions `workflow_dispatch`.
- Optional demo reseed can be triggered during manual dispatch.

Required GitHub Secrets (staging):

- `STAGING_SSH_HOST`
- `STAGING_SSH_USER`
- `STAGING_SSH_KEY`
- `STAGING_DEPLOY_PATH`
- optional: `STAGING_SSH_PORT` (default `22`)
- optional: `STAGING_ENABLE_CADDY` (`true`/`false`)

Required GitHub Secrets (production):

- `PRODUCTION_SSH_HOST`
- `PRODUCTION_SSH_USER`
- `PRODUCTION_SSH_KEY`
- `PRODUCTION_DEPLOY_PATH`
- optional: `PRODUCTION_SSH_PORT` (default `22`)
- optional: `PRODUCTION_ENABLE_CADDY` (`true`/`false`)

GitHub Environments:

- Create `staging` environment.
- Create `production` environment and add required reviewer approvals.
