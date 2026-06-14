# Architecture & Technical Details

Last updated: 2026-06-14

This document serves as the technical companion to the [README.md](../README.md), focusing on system design, data flow, and core implementation details of the Atticus platform.

## System Architecture

Atticus is built on a modern, decoupled architecture separating the client, API backend, and asynchronous workers.

```mermaid
graph TD
    Client[Next.js Client] -->|REST & SSE| API[FastAPI Backend]
    API -->|Read/Write| DB[(PostgreSQL)]
    API -->|Cache/Queue| Redis[(Redis)]
    API -->|Dense Search| Qdrant[(Qdrant)]
    API -->|Sparse Search| ES[(Elasticsearch)]
    API -->|LLM Requests| Ollama[Local Ollama]
    
    Redis -->|Tasks| Celery[Celery Worker]
    Celery -->|Ingestion| DB
    Celery -->|Index| Qdrant
    Celery -->|Index| ES
    
    API -.->|Tracing| Langfuse[Langfuse]
```

## Security & Access Model

- **App Roles**: `admin`, `lawyer`
- **Access Model**: Multi-tenant-like isolation at the case level. Both role checks and case assignment checks (`assigned_lawyers`) are strictly enforced.

## Document Ingestion Pipeline

The ingestion process is completely asynchronous, relying on Celery to handle computationally expensive tasks like parsing, chunking, and embedding.

```mermaid
sequenceDiagram
    participant User
    participant API
    participant Celery
    participant Qdrant
    participant ES

    User->>API: Upload Document (.pdf, .docx, etc)
    API->>API: Write to /tmp/atticus_uploads
    API->>DB: Create Document (status: processing)
    API->>Celery: Enqueue Ingestion Job
    API-->>User: Return Job ID
    
    Celery->>Celery: Detect File Type & Parse Text
    Celery->>Celery: Classify Document Type
    Celery->>Celery: Apply Chunker (Email, Deposition, etc)
    Celery->>Celery: Generate Embeddings (sentence-transformers)
    Celery->>Qdrant: Index Dense Vectors
    Celery->>ES: Index Sparse Tokens
    Celery->>DB: Update Document (status: completed)
```

### Chunking Strategies
We use specialized chunkers to handle the unique structure of different legal documents:
- `EmailChunker`: Preserves metadata (From, To, Date) alongside email body.
- `DepositionChunker`: Preserves Q&A cadence and speaker boundaries.
- `SectionedChunker`: Ideal for formal briefs with clear headings.
- `NarrativeChunker`: Optimized for continuous prose and reports.
- `UnstructuredChunker`: Fallback chunker for raw text files.

## Hybrid Retrieval Pipeline

To ensure the highest accuracy for legal queries, Atticus uses a two-stage hybrid retrieval system combining semantic understanding with exact keyword matching.

```mermaid
graph LR
    Query[User Query] --> Embed[Embed Query]
    Embed --> SemanticCache{Semantic Cache Hit?}
    SemanticCache -- Yes --> ReturnCache[Return Cached Result]
    SemanticCache -- No --> Rewrite[Rewrite Ambiguous Query]
    
    Rewrite --> DenseSearch[Qdrant Dense Search]
    Rewrite --> SparseSearch[Elasticsearch Sparse Search]
    
    DenseSearch --> RRF[Reciprocal Rank Fusion]
    SparseSearch --> RRF
    
    RRF --> Reranker[Cross-Encoder Reranker]
    Reranker --> Generation[LLM Generation Context]
```

## Data Model

**Core Tables:**
- `users`: Authentication and role data.
- `cases`: The root boundary for document isolation.
- `documents`: Metadata and sync status for uploaded files.
- `ingestion_jobs`: Granular state tracking of the ingestion worker.
- `conversations` & `messages`: Chat history tracking.

**Database Migrations:**
Handled via plain SQL migrations applied sequentially on startup (`backend/scripts/apply_migrations.py`).

## Core API Map

- **Auth**: `/auth/register`, `/auth/login`, `/auth/logout`, `/auth/me`
- **Cases**: `/cases`, `/cases/{case_id}`, `/cases/lawyers`, `/cases/demo/reset`
- **Documents**: `/cases/{case_id}/documents/*`
- **Ingestion**: `/ingestion/jobs`, `/ingestion/jobs/{file_id}`
- **Chat**: `/chat`, `/chat/stream`, `/chat/conversations/*`
- **Health**: `/health`, `/ready`

## Operations & Scripts

To manipulate data locally or in demo environments:

- `backend/scripts/reset_demo_data.py`: Clears existing demo objects.
- `backend/scripts/seed_demo_data.py`: Seeds the system with the Finch Demo Matter.
- `backend/scripts/reset_and_seed_demo_data.py`: Combined orchestration script.
