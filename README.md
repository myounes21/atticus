<div align="center">
  <h1>Atticus</h1>
  <p><strong>A private legal workspace for case-scoped document search and cited AI answers.</strong></p>

  [![Python](https://img.shields.io/badge/Python-3.12-blue?logo=python&logoColor=white)](https://python.org)
  [![Next.js](https://img.shields.io/badge/Next.js-15-black?logo=next.js&logoColor=white)](https://nextjs.org)
  [![React](https://img.shields.io/badge/React-19-blue?logo=react&logoColor=white)](https://react.dev)
  [![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
  [![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)](https://docker.com)
</div>

<br />

## About The Project

Atticus is a comprehensive full-stack application designed specifically for legal professionals. It provides a secure, role-based workspace where lawyers can upload case files, and leverage state-of-the-art hybrid retrieval and local Large Language Models (LLMs) to interact with their documents. 

By keeping all document ingestion, embedding, and generation in-house (or self-hosted), Atticus guarantees data privacy while providing lightning-fast, cited answers to complex legal queries.

## Key Features

- **Role-Based Access Control**: Built-in `admin` and `lawyer` roles. Case visibility is strictly scoped via `assigned_lawyers`.
- **Robust Document Ingestion**: Supports `.pdf`, `.docx`, `.txt`, and `.eml` files with an asynchronous, robust ingestion pipeline (parsing, chunking, indexing).
- **Advanced Hybrid Retrieval**: Combines dense vector search (Qdrant) and sparse keyword search (Elasticsearch) via Reciprocal Rank Fusion (RRF), capped off with cross-encoder reranking.
- **Streaming AI Chat with Citations**: Server-Sent Events (SSE) stream the AI's response in real-time, injecting inline citations pointing exactly to the source documents.
- **Seamless Deployment**: fully containerized with Docker Compose for local development, demo environments, and production deployment.

## Technology Stack

| Category | Technologies |
| --- | --- |
| **Frontend** | Next.js 15, React 19, TypeScript, Tailwind CSS |
| **Backend** | FastAPI (Python 3.12), Pydantic, Celery |
| **Databases** | PostgreSQL (Relational), Redis (Cache/Queue) |
| **Search & Vector DB**| Qdrant (Dense), Elasticsearch (Sparse) |
| **AI / Machine Learning** | Local Ollama (`llama3.3:70b`), `sentence-transformers` |
| **Observability** | Langfuse |

## Quick Start

### Prerequisites
- [Docker](https://docs.docker.com/get-docker/) and Docker Compose
- Ensure you have sufficient resources to run `llama3.3:70b` locally or update the model configuration.

### Installation

1. **Start the application stack**
   ```bash
   docker compose up --build -d
   ```

2. **Pull the LLM model**
   ```bash
   docker compose exec ollama ollama pull llama3.3:70b
   ```

3. **Seed demo data**
   ```bash
   docker compose --profile demo run --rm demo-seed
   ```

4. **Access the application**
   Open your browser and navigate to `http://localhost:3000`.

### Health Checks

Verify the backend is ready:
```bash
curl -f http://localhost:8000/ready
```
Check running containers and logs:
```bash
docker compose ps
docker compose logs -f backend
```

## Demo Experience

Experience the platform using our seeded demo data (the *Finch Demo Matter* case). 

**Demo Accounts:**
- **Admin:** `demo.admin@atticus.local` | `DemoPass!123`
- **Lawyer:** `demo.lawyer@atticus.local` | `DemoPass!123`

To reset and re-seed demo content at any time:
```bash
docker compose --profile demo run --rm demo-seed
```

## Documentation

For a deep dive into the system design, APIs, and deployment, please refer to the following documentation:

- **[Architecture & Technical Details](docs/ARCHITECTURE.md)**: Explore the system snapshot, ingestion pipeline, hybrid retrieval logic, and database schemas.
- **[Deployment Runbook](docs/DEPLOYMENT.md)**: Step-by-step guide for staging and production deployments, including CI/CD and HTTPS proxy setup.

## Testing and Validation

Validate the codebase using built-in scripts:

```bash
# Frontend Lints and Build
cd frontend
npm run lint && npm run build

# Backend Tests
cd ../backend
uv run pytest
```

### Benchmarking and Evaluation

To generate real metrics for pipeline latency and quality, run the following evaluation scripts in order:

1. **Run Ablation Study** (Measures Hit Rate@3 across 4 retrieval architectures):
   ```bash
   export $(grep -v '^#' .env | xargs) && uv run python tests/evaluation/test_retrieval_ablation.py
   ```
2. **Run RAGAS Quality Evaluation** (Evaluates Context Precision/Recall, Faithfulness, Relevancy):
   ```bash
   export $(grep -v '^#' .env | xargs) && uv run python tests/evaluation/test_ragas.py
   ```
3. **Load Testing - Cache Hit/Miss** (Measures latency delta with Locust):
   ```bash
   export $(grep -v '^#' .env | xargs) && uv run locust -f tests/load/locustfile.py
   ```
4. **Ingestion Throughput** (Calculates chunks/sec and pages/min):
   ```bash
   export $(grep -v '^#' .env | xargs) && uv run python tests/load/test_ingestion_throughput.py
   ```

---

<div align="center">
  <p>Built by an engineer passionate about intuitive design and scalable architecture.</p>
</div>
