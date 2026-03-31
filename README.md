# Atticus

Atticus is a private legal intelligence workspace with strict case scoping, role-based access, and cited answers over uploaded documents.

## Live Demo (CV Ready)

- Roles are intentionally simple: `admin` and `lawyer`.
- Default demo credentials (after seeding):
  - Admin: `demo.admin@atticus.local` / `DemoPass!123`
  - Lawyer: `demo.lawyer@atticus.local` / `DemoPass!123`
- Demo flow (about 60 seconds):
  1. Sign in as admin and confirm cases/documents exist.
  2. Sign in as lawyer and open a seeded case.
  3. Ask a question and verify response includes source context.

## Architecture

- Frontend: Next.js 15 (App Router), TypeScript.
- Backend: FastAPI + PostgreSQL.
- Retrieval: Qdrant (dense) + Elasticsearch (sparse) + RRF + reranking.
- Cache/async: Redis + Celery ingestion queue.
- Security: JWT auth, role checks, case-level access control, request rate limits.

## Recent Updates

- Lawyers assigned to a case can upload documents (admin upload is still supported).
- Chat streaming now handles SSE chunks more robustly and renders markdown (lists, links, code blocks, quotes) in the UI.
- Added unit coverage for streaming chat events (`token`, `done`, `error`) in `tests/unit/test_chat_stream_api.py`.
- General cleanup removed dead imports/unused code paths to keep lint and builds clean.

## Run Locally

1. Create env file:
   - `cp .env.example .env`
2. Start stack:
   - `docker compose up --build -d`
3. Apply demo seed data:
   - `docker compose --profile demo run --rm demo-seed`
4. Open app:
   - `http://localhost:3000`

Useful checks:
- `docker compose ps`
- `docker compose logs -f backend`
- Backend readiness: `http://localhost:8000/ready`

## Deployment (HTTPS)

This repo includes Caddy reverse proxy config for TLS termination.

1. Set production values in `.env`:
   - `APP_ENV=production`
   - `APP_DOMAIN=<your-domain>`
   - `ALLOWED_ORIGINS=["https://<your-domain>"]`
   - strong `JWT_SECRET_KEY`
   - strong `POSTGRES_PASSWORD`
   - `DEMO_AUTH=false`
   - `ENABLE_SELF_REGISTER=false`
   - `NEXT_PUBLIC_DEMO_AUTH=false`
   - `NEXT_PUBLIC_ENABLE_SELF_REGISTER=false`
2. Start services:
   - `docker compose up --build -d`
3. Start HTTPS proxy:
   - `docker compose --profile prod up -d caddy`

## CI/CD

- CI checks run on PRs and push to `main` via `.github/workflows/eval_gate.yml`.
- CD deploy workflow is in `.github/workflows/deploy_cd.yml`:
  - auto deploy to `staging` on push to `main` (when staging secrets are configured),
  - manual deploy to `production` via workflow dispatch.
- Full setup steps and secret list are in `docs/DEPLOYMENT.md`.

## Demo Dataset Management

- Seed deterministic demo data:
  - `docker compose --profile demo run --rm demo-seed`
- Reset and reseed manually from backend container:
  - `uv run python backend/scripts/reset_and_seed_demo_data.py`
- Individual scripts:
  - `uv run python backend/scripts/reset_demo_data.py`
  - `uv run python backend/scripts/seed_demo_data.py`

Seeded synthetic docs are in `backend/demo_data`.

## Safety and Hardening Included

- Role model reduced to `admin` and `lawyer` only.
- Registration toggle enforced server-side (`ENABLE_SELF_REGISTER`).
- Production validator rejects unsafe config (`demo_auth`/self-register enabled, weak JWT, wildcard origins).
- Rate limits:
  - login
  - chat
  - uploads
- Upload safeguards:
  - max size configured by `UPLOAD_MAX_MB`
  - extension allow-list via `UPLOAD_ALLOWED_EXTENSIONS`
- Input limits for case names and chat query size.

## Langfuse Observability (Metadata-Only)

- Optional Langfuse Cloud tracing is supported for chat/retrieval/generation/ingestion.
- Default mode is metadata-only (no prompt or document text content).
- Enable via env:
  - `LANGFUSE_ENABLED=true`
  - `LANGFUSE_PUBLIC_KEY=<key>`
  - `LANGFUSE_SECRET_KEY=<key>`
  - `LANGFUSE_BASE_URL=https://cloud.langfuse.com`
  - `LANGFUSE_CAPTURE_CONTENT=false`

## Migrations

- SQL migrations are in `backend/migrations`.
- Containers run migration bootstrap automatically via:
  - `backend/scripts/apply_migrations.py`
- Migration `002_roles_and_hardening.sql` converts legacy `paralegal` users to `lawyer` and tightens role constraints.

## Validation Commands

- Frontend:
  - `cd frontend && npm run lint && npm run build`
- Backend tests:
  - `uv run pytest`

## Known Tradeoffs

- Demo seed uses deterministic synthetic text files for reliability, not real legal records.
- Full pipeline quality depends on external model/API availability and infra resources.
- Local Docker composition prioritizes reproducibility over minimal memory footprint.
