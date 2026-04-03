# Atticus Documentation (Implementation Notes)

Last updated: 2026-04-03

This is the concise technical companion to `README.md`, focused on how the current codebase works.

## Current System Snapshot

- App roles: `admin`, `lawyer`
- Access model: role checks + case assignment checks (`assigned_lawyers`)
- Upload types: `.pdf`, `.docx`, `.txt`, `.eml`
- Ingestion: async pipeline with job state tracking
- Retrieval: dense + sparse + fusion + rerank
- Chat: non-stream and SSE stream with citations

## Stack and Runtime

- Frontend: Next.js 15 / React 19 / TypeScript
- Backend: FastAPI / Python 3.12
- Storage/search: PostgreSQL, Qdrant, Elasticsearch, Redis
- Worker: Celery (with fallback patterns in route/task flow)
- LLM calls: local Ollama client (`ollama_model`)
- Observability: required Langfuse, metadata-only by default

Notable current implementation behavior:

- Embeddings are model-backed via `sentence-transformers` (`BAAI/bge-m3`) with optional deterministic fallback.
- Production mode enforces `embedding_backend != fallback` and `embedding_fallback_enabled=false`.
- Reranker uses CrossEncoder when available, else identity fallback.

## Data and Migrations

Core tables:

- `users`, `cases`, `documents`, `conversations`, `messages`, `ingestion_jobs`

Migrations:

- `backend/migrations/001_initial.sql`
- `backend/migrations/002_roles_and_hardening.sql`
- `backend/migrations/003_user_full_name.sql`

Apply script:

- `backend/scripts/apply_migrations.py`

## API Map

Auth:

- `POST /auth/register`
- `POST /auth/login`
- `POST /auth/logout`
- `GET /auth/me`

Cases:

- `POST /cases` (admin)
- `GET /cases`
- `GET /cases/{case_id}`
- `PATCH /cases/{case_id}` (admin)
- `DELETE /cases/{case_id}` (admin)
- `GET /cases/lawyers` (admin)
- `POST /cases/demo/reset` (admin; blocked in production)

Documents:

- `POST /cases/{case_id}/documents/upload`
- `GET /cases/{case_id}/documents`
- `GET /cases/{case_id}/documents/{file_id}`
- `PATCH /cases/{case_id}/documents/{file_id}` (admin)
- `DELETE /cases/{case_id}/documents/{file_id}` (admin)

Ingestion:

- `POST /ingestion/jobs`
- `GET /ingestion/jobs/{file_id}`

Chat:

- `POST /chat`
- `POST /chat/stream`
- `GET /chat/conversations`
- `GET /chat/conversations/{conversation_id}`
- `DELETE /chat/conversations/{conversation_id}`

Health:

- `GET /health`
- `GET /ready`

## Ingestion Details

Upload path (`/cases/{case_id}/documents/upload`) currently:

1. Validates size/extension.
2. Writes a local temp copy in `/tmp/atticus_uploads`.
3. Attempts S3 upload first when configured (`documents/{case_id}/{file_id}/{name}`).
4. Persists `documents.s3_key` on S3 success; otherwise temp file remains fallback source.
5. Creates `documents` row (`processing`) and runs async ingestion task.

Pipeline stages:

- file type detect -> parse -> doc type detect -> chunk -> prefix enrich -> embed -> index

Status model:

- `queued -> running -> indexing -> completed`
- or terminal `review_required` / `failed`

Detection behavior:

- `.eml` shortcut => `email`
- short `.txt` shortcut => `note`
- else LLM classifier; unknown => `review_required`

Chunkers in active code:

- `EmailChunker`, `DepositionChunker`, `SectionedChunker`, `NarrativeChunker`, `UnstructuredChunker`

## Retrieval and Generation Details

Retrieval pipeline:

1. Embed query
2. Check semantic cache
3. Rewrite short/ambiguous query when applicable
4. Dense (Qdrant) + sparse (Elasticsearch)
5. RRF fusion
6. Rerank top results

Generation:

- General queries can bypass retrieval.
- Case/document queries use retrieved context and prompt builder.
- Responses can be streamed as SSE (`token`, `citation`, `done`, `error`).

## Frontend Notes

Primary routes:

- `/` login + demo launcher
- `/admin` admin workspace
- `/lawyer` lawyer workspace

Implemented UX pieces include:

- case selection/creation and assignment UI
- document listing/upload
- streamed markdown chat output with citation chips

## Operations

Demo scripts:

- `backend/scripts/reset_demo_data.py`
- `backend/scripts/seed_demo_data.py`
- `backend/scripts/reset_and_seed_demo_data.py`

Docker profiles:

- `demo`: reseed job
- `prod`: Caddy
- `ops`: periodic Postgres backup

CI/CD workflows:

- CI: `.github/workflows/eval_gate.yml`
- CD: `.github/workflows/deploy_cd.yml`
