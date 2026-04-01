# Atticus

Atticus is a private legal workspace for case-scoped document search and cited AI answers.

It ships as a full-stack app with role-based access, document ingestion, hybrid retrieval, and chat (including streaming).

## Highlights

- Two roles: `admin`, `lawyer`
- Case-level visibility via `assigned_lawyers`
- Upload support: `.pdf`, `.docx`, `.txt`, `.eml`
- Async ingestion with job statuses
- Hybrid retrieval: Qdrant + Elasticsearch + RRF + rerank
- Chat endpoints: standard + SSE stream with citation events
- Docker Compose workflows for local/dev and deployment

## Stack

- Frontend: Next.js 15, React 19, TypeScript
- Backend: FastAPI (Python 3.12)
- Data: PostgreSQL
- Search: Qdrant (dense), Elasticsearch (sparse)
- Cache/Queue: Redis + Celery
- LLM: Groq API
- Optional tracing: Langfuse (metadata-only by default)

## Quick Start

```bash
cp .env.example .env
docker compose up --build -d
docker compose --profile demo run --rm demo-seed
```

Open `http://localhost:3000`.

Useful checks:

```bash
docker compose ps
docker compose logs -f backend
```

Backend readiness: `http://localhost:8000/ready`

## Demo Accounts

- `demo.admin@atticus.local` / `DemoPass!123`
- `demo.lawyer@atticus.local` / `DemoPass!123`

## Demo Dataset

- Seeded case: `Finch Demo Matter` (client: `Finch Legal Demo`)
- Source directory: `demo data/`
- Included files:
  - `defense_brief_v1.docx`
  - `prosecution_brief_v1.docx`
  - `medical_report.pdf`
  - `mayella_ewell_deposition.txt`
  - `tom_robinson_deposition.txt`
  - `sheriff_tate_deposition.txt`
  - `witness_statement_bob_ewell.docx`
  - `incident_timeline.txt`
  - `strategy_notes.txt`
  - `contradictions_log.txt`
  - `strategy_discussion.eml`

To reset and reseed demo content:

```bash
docker compose --profile demo run --rm demo-seed
```

## Core API Surface

- Auth: `/auth/register`, `/auth/login`, `/auth/logout`, `/auth/me`
- Cases: `/cases`, `/cases/{case_id}`, `/cases/lawyers`, `/cases/demo/reset`
- Documents: `/cases/{case_id}/documents/*`
- Ingestion: `/ingestion/jobs`, `/ingestion/jobs/{file_id}`
- Chat: `/chat`, `/chat/stream`, `/chat/conversations/*`

## Deployment

- Standard app stack: `docker compose up --build -d`
- HTTPS proxy (Caddy): `docker compose --profile prod up -d caddy`
- Full runbook: `docs/DEPLOYMENT.md`

## CI/CD

- CI checks: `.github/workflows/eval_gate.yml`
- Deploy workflow: `.github/workflows/deploy_cd.yml`

## Practical Notes

- Retrieval and route handlers enforce case scoping (`case_id`, `assigned_lawyers`, `is_latest`).
- Embeddings currently use a deterministic fallback embedder in `backend/models/embedder.py`.
- Reranker falls back gracefully if CrossEncoder runtime deps are unavailable.
- Some evaluation/legal-safety test files are present as placeholders.

## Validation

```bash
cd frontend && npm run lint && npm run build
uv run pytest
```

## More Details

For implementation-accurate technical notes, see `atticus_documentaion.md`.
