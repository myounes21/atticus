"Atticus Finch won his cases by reading every document carefully and finding the truth others missed. That's exactly what this platform does for your firm."

## Ideas

- Private, self-hosted legal intelligence pipeline for case documents.
- Domain-based organization across ingestion, retrieval, generation, and safety.
- Safety-first behavior with case isolation, RBAC enforcement, and citation checks.
- Constant organization split by scope:
  - shared domain constants in `backend/core/constants.py`
  - detection constants in `backend/ingestion/detection/constants.py`
  - parser/chunker constants in their domain folders

## Tools

- Python `>=3.12`
- FastAPI backend + Next.js frontend
- `groq` for LLM integration
- `pdfplumber`, `python-docx`, stdlib email parser
- Qdrant + Elasticsearch + Redis + Postgres integrations
- `pytest` test suites (`unit`, `legal_safety`, `evaluation`)
- Docker and docker compose for local stack

## File Structure

```
Atticus/
│
├── pyproject.toml
├── uv.lock
├── docker-compose.yml
├── .env
├── .env.example
├── .gitignore
├── README.md
├── config.py
│
├── backend/
│   ├── __init__.py
│   ├── Dockerfile
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   ├── main.py
│   │   ├── routes/
│   │   │   ├── __init__.py
│   │   │   ├── auth.py
│   │   │   ├── cases.py
│   │   │   ├── documents.py
│   │   │   └── chat.py
│   │   └── middleware/
│   │       ├── __init__.py
│   │       ├── auth_middleware.py
│   │       └── rbac_middleware.py
│   │
│   ├── core/
│   │   ├── __init__.py
│   │   ├── constants.py
│   │   ├── security.py
│   │   └── dependencies.py
│   │
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── case.py
│   │   ├── document.py
│   │   ├── user.py
│   │   └── chat.py
│   │
│   ├── ingestion/
│   │   ├── __init__.py
│   │   ├── parsers/
│   │   │   ├── __init__.py
│   │   │   ├── base.py
│   │   │   ├── constants.py
│   │   │   ├── pdf_parser.py
│   │   │   ├── docx_parser.py
│   │   │   ├── eml_parser.py
│   │   │   ├── txt_parser.py
│   │   │   ├── parser_factory.py
│   │   │   └── pipeline.py
│   │   ├── detection/
│   │   │   ├── __init__.py
│   │   │   ├── constants.py
│   │   │   ├── detector.py
│   │   │   ├── file_type_detector.py
│   │   │   └── doc_type_detector.py
│   │   ├── chunkers/
│   │   │   ├── __init__.py
│   │   │   ├── base.py
│   │   │   ├── constants.py
│   │   │   ├── contract_chunker.py
│   │   │   ├── brief_chunker.py
│   │   │   ├── email_chunker.py
│   │   │   └── note_chunker.py
│   │   ├── enrichment/
│   │   │   ├── __init__.py
│   │   │   └── prefix_enricher.py
│   │   └── indexers/
│   │       ├── __init__.py
│   │       ├── qdrant_indexer.py
│   │       └── elastic_indexer.py
│   │
│   ├── retrieval/
│   │   ├── __init__.py
│   │   ├── pipeline.py
│   │   ├── query_rewriter.py
│   │   ├── dense_search.py
│   │   ├── sparse_search.py
│   │   ├── rrf.py
│   │   ├── reranker.py
│   │   └── cache/
│   │       ├── __init__.py
│   │       ├── semantic_cache.py
│   │       └── cache_invalidator.py
│   │
│   ├── generation/
│   │   ├── __init__.py
│   │   ├── pipeline.py
│   │   ├── prompt_builder.py
│   │   ├── chat_history.py
│   │   ├── llm_client.py
│   │   └── streamer.py
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   ├── embedder.py
│   │   └── reranker.py
│   │
│   ├── db/
│   │   ├── __init__.py
│   │   ├── postgres.py
│   │   ├── qdrant.py
│   │   ├── elastic.py
│   │   └── redis.py
│   │
│   ├── storage/
│   │   ├── __init__.py
│   │   └── s3.py
│   │
│   ├── tasks/
│   │   ├── __init__.py
│   │   ├── celery_app.py
│   │   └── ingest_task.py
│   │
│   └── migrations/
│       └── 001_initial.sql
│
├── frontend/
│   ├── Dockerfile
│   ├── package.json
│   └── src/
│       ├── app/
│       │   ├── admin/
│       │   └── lawyer/
│       ├── components/
│       │   ├── chat/
│       │   ├── cases/
│       │   └── documents/
│       └── lib/
│           ├── api.ts
│           └── auth.ts
│
├── tests/
│   ├── evaluation/
│   │   ├── golden_dataset.json
│   │   └── test_ragas.py
│   ├── legal_safety/
│   │   ├── test_rbac.py
│   │   ├── test_case_isolation.py
│   │   ├── test_versioning.py
│   │   └── test_citations.py
│   └── unit/
│       ├── test_parsers.py
│       ├── test_detectors.py
│       ├── test_chunkers.py
│       ├── test_eml_parser.py
│       └── test_doc_type_detector_unknown.py
│
├── playground/
│   ├── email_test.ipynb
│   ├── pdf_test.ipynb
│   ├── test_doc_det.ipynb
│   └── txt.ipynb
│
├── test_files/
    ├── Dead Poets Society.pdf
    ├── test_email.eml
    └── test_txtparser.txt

└── .github/
    └── workflows/
        └── eval_gate.yml
```

