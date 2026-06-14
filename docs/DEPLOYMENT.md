# Deployment Runbook

This guide covers everything required to deploy Atticus from a local environment all the way to production.

> [!IMPORTANT]
> The default `.env` configuration is tuned for local development. For staging or production environments, you **must** configure secure credentials and enable observability features.

## Table of Contents
1. [Environment Configuration](#1-environment-configuration)
2. [Starting the Application](#2-starting-the-application)
3. [Reverse Proxy (Caddy)](#3-reverse-proxy-caddy)
4. [Demo Environments](#4-demo-environments)
5. [CI/CD Setup](#5-cicd-setup)
6. [Operations & Recovery](#6-operations--recovery)

---

## 1. Environment Configuration

From the repository root, copy the production template to initialize your configuration:

```bash
cp .env.production.example .env
```

### Core Environment Variables

| Variable | Description | Example / Recommended Value |
| --- | --- | --- |
| `APP_ENV` | Application environment (`development`, `staging`, `production`) | `production` |
| `APP_DOMAIN` | The public domain name for the application | `atticus.yourdomain.com` |
| `ALLOWED_ORIGINS` | JSON list of allowed CORS origins | `["https://atticus.yourdomain.com"]` |
| `JWT_SECRET_KEY` | Secret key for issuing access tokens | `<long-random-string>` |
| `POSTGRES_PASSWORD` | PostgreSQL database password | `<strong-password>` |
| `ELASTICSEARCH_PASSWORD`| Elasticsearch security password | `<strong-password>` |

> [!WARNING]
> In `APP_ENV=production`, the application will block startup if `EMBEDDING_FALLBACK_ENABLED=true`. You must ensure that the model backend (`BAAI/bge-m3`) is fully loaded.

### Observability Configuration (Langfuse)

Langfuse tracing is strictly required for monitoring LLM interactions and generation quality.

| Variable | Description |
| --- | --- |
| `LANGFUSE_PUBLIC_KEY` | Public API key |
| `LANGFUSE_SECRET_KEY` | Secret API key |
| `LANGFUSE_BASE_URL` | e.g. `https://cloud.langfuse.com` |
| `LANGFUSE_CAPTURE_CONTENT` | Set to `false` in production to prevent logging PII/client data |

---

## 2. Starting the Application

Build and start the core Docker Compose stack in detached mode:

```bash
docker compose up --build -d
```

**Health Verification:**
Validate that the FastAPI backend is running and the embedding backend is ready to serve traffic:
```bash
docker compose ps
curl -f http://localhost:8000/ready
```

---

## 3. Reverse Proxy (Caddy)

Atticus includes a Caddy profile configured to automatically handle SSL certificates and reverse-proxy traffic to the frontend and backend.

1. Ensure your DNS points your `APP_DOMAIN` to the server IP.
2. Start the Caddy service using the `prod` profile:
   ```bash
   docker compose --profile prod up -d caddy
   ```
3. Monitor the proxy to ensure SSL generation succeeds:
   ```bash
   docker compose logs -f caddy
   ```

---

## 4. Demo Environments

To launch a demo instance (e.g., for sales or a portfolio showcase), run the deterministic reset and seed job.

> [!NOTE]
> This command will wipe the current database state and load the Finch Demo Matter case along with its sample files and user accounts.

```bash
docker compose --profile demo run --rm demo-seed
```

---

## 5. CI/CD Setup

We utilize GitHub Actions to automate testing and deployments.

- **CI Gate (`.github/workflows/eval_gate.yml`)**: Runs linting, unit tests, and evaluation metrics on all PRs.
- **CD Deploy (`.github/workflows/deploy_cd.yml`)**: Automates deployment to staging and production.

### Deployment Triggers
- **Staging**: Pushing or merging to the `main` branch auto-deploys to staging.
- **Production**: Strictly **manual** via GitHub Actions `workflow_dispatch` (requires environment approval).

### Required GitHub Secrets

You must configure the following secrets in your repository settings:

| Secret | Target | Description |
| --- | --- | --- |
| `STAGING_SSH_HOST` | Staging | The SSH host/IP address for the staging server |
| `STAGING_SSH_USER` | Staging | The SSH user |
| `STAGING_SSH_KEY` | Staging | The private SSH key for the action runner |
| `STAGING_DEPLOY_PATH` | Staging | The absolute path on the server to deploy to |
| `PRODUCTION_SSH_*` | Production| Corresponding secrets for the production environment |

*Optional CI/CD Variables:* `STAGING_SSH_PORT` (default 22), `STAGING_ENABLE_CADDY` (`true`/`false`).

---

## 6. Operations & Recovery

### Standard Commands

**Tail all logs:**
```bash
docker compose logs -f backend frontend celery-worker
```

**Restart a specific service:**
```bash
docker compose restart backend
```

**Full restart and rebuild:**
```bash
docker compose down && docker compose up --build -d
```

### Backups

To run a periodic or one-off PostgreSQL backup via the ops profile:
```bash
docker compose --profile ops up -d postgres-backup
```
