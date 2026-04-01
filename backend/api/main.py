import logging

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware

from backend.api.middleware.auth_middleware import AuthMiddleware
from backend.api.routes.auth import router as auth_router
from backend.api.routes.cases import router as cases_router
from backend.api.routes.chat import router as chat_router
from backend.api.routes.documents import router as documents_router
from backend.api.routes.ingestion import router as ingestion_router
from backend.db.elastic import get_client as get_es_client
from backend.db.postgres import fetch_optional
from backend.db.qdrant import get_client as get_qdrant_client
from backend.db.redis import get_client as get_redis_client
from config import settings

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Atticus API",
    description="Legal Intelligence Platform — private, self-hosted RAG for law firms",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(AuthMiddleware)

app.include_router(auth_router)
app.include_router(cases_router)
app.include_router(documents_router)
app.include_router(chat_router)
app.include_router(ingestion_router)


@app.get("/health", tags=["health"])
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/ready", tags=["health"])
def readiness_check() -> dict[str, str]:
    try:
        fetch_optional("SELECT 1")
        get_redis_client().ping()
        get_qdrant_client().get_collections()
        if not get_es_client().ping():
            raise RuntimeError("Elasticsearch ping failed")
        return {"status": "ready"}
    except Exception as exc:
        logger.exception("Readiness probe failed")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service dependencies are not ready",
        ) from exc
