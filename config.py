from pathlib import Path
import json
from typing import ClassVar, Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

ENV_PATH = Path(__file__).resolve().parent / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ENV_PATH, extra="ignore")

    # LLM
    groq_api_key: str = ""
    groq_llm_model: str = "llama-3.3-70b-versatile"

    # Document detector configs
    detection_snippet_length: int = 1000

    # Chunking configs
    CHUNK_SIZE_MIN: ClassVar[int] = 300
    CHUNK_SIZE_MAX: ClassVar[int] = 500
    CHUNK_OVERLAP: ClassVar[int] = 50

    # Embedder
    embedder_model: str = "BAAI/bge-m3"
    embedding_dimension: int = 1024

    # Reranker (HuggingFace only)
    huggingface_reranker_model: str = "BAAI/bge-reranker-base"

    # Qdrant
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    qdrant_collection_name: str = "chunks"

    # Elasticsearch
    elasticsearch_host: str = "localhost"
    elasticsearch_port: int = 9200
    elasticsearch_password: str = ""
    elasticsearch_index_name: str = "chunks"

    # Redis
    redis_host: str = "localhost"
    redis_port: int = 6379

    # AWS S3
    s3_bucket_name: str = "atticus-documents"
    s3_region: str = "us-east-1"
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""

    # JWT
    jwt_secret_key: str = "CHANGE-ME-IN-PRODUCTION"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60  # 1 hour
    jwt_issuer: str = "atticus-api"
    jwt_audience: str = "atticus-clients"

    # MVP auth mode
    demo_auth: bool = False
    demo_auth_default_role: Literal["lawyer"] = "lawyer"
    enable_self_register: bool = False

    # PostgreSQL
    database_url: str = "sqlite:///atticus.db"

    # Input and upload safety
    upload_max_mb: int = 20
    upload_allowed_extensions: list[str] = Field(
        default_factory=lambda: [".pdf", ".docx", ".txt", ".eml"]
    )
    max_chat_query_chars: int = 2500
    max_case_name_chars: int = 140
    max_client_name_chars: int = 140

    # Abuse protection
    rate_limit_login_requests: int = 8
    rate_limit_login_window_seconds: int = 60
    rate_limit_chat_requests: int = 30
    rate_limit_chat_window_seconds: int = 60
    rate_limit_upload_requests: int = 12
    rate_limit_upload_window_seconds: int = 300

    # Semantic cache
    cache_ttl_seconds: int = 3600
    cache_similarity_threshold: float = 0.95

    # Langfuse observability
    langfuse_enabled: bool = False
    langfuse_public_key: str = ""
    langfuse_secret_key: str = ""
    langfuse_base_url: str = "https://cloud.langfuse.com"
    langfuse_capture_content: bool = False

    # Retrieval pipeline
    retrieval_top_k: int = 12
    rrf_top_k: int = 10
    rerank_top_k: int = 3

    app_port: int = 8000

    app_env: str = "development"
    allowed_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:3000"]
    )

    @field_validator("upload_allowed_extensions", mode="before")
    @classmethod
    def normalize_upload_extensions(cls, value: object) -> list[str]:
        if isinstance(value, str):
            raw = value.strip()
            if raw.startswith("[") and raw.endswith("]"):
                parsed = json.loads(raw)
                if not isinstance(parsed, list):
                    raise ValueError(
                        "upload_allowed_extensions JSON value must be a list"
                    )
                items = [str(item).strip() for item in parsed if str(item).strip()]
            else:
                items = [item.strip() for item in raw.split(",") if item.strip()]
        elif isinstance(value, list):
            items = [str(item).strip() for item in value if str(item).strip()]
        else:
            raise ValueError(
                "upload_allowed_extensions must be a list or comma-separated string"
            )

        normalized: list[str] = []
        for item in items:
            ext = item.lower()
            if not ext.startswith("."):
                ext = f".{ext}"
            normalized.append(ext)

        if not normalized:
            raise ValueError("upload_allowed_extensions cannot be empty")
        return sorted(set(normalized))

    @model_validator(mode="after")
    def validate_production_settings(self) -> "Settings":
        if self.upload_max_mb < 1:
            raise ValueError("upload_max_mb must be at least 1")
        if self.max_chat_query_chars < 200:
            raise ValueError("max_chat_query_chars must be at least 200")

        if self.app_env.lower() == "production":
            if (
                self.jwt_secret_key in {"", "CHANGE-ME-IN-PRODUCTION"}
                or len(self.jwt_secret_key) < 32
            ):
                raise ValueError(
                    "jwt_secret_key must be set to a strong value in production"
                )
            if not self.allowed_origins:
                raise ValueError("allowed_origins must be set in production")
            if "*" in self.allowed_origins:
                raise ValueError("allowed_origins cannot contain '*' in production")
            if self.demo_auth:
                raise ValueError("demo_auth must be disabled in production")
            if self.enable_self_register:
                raise ValueError("enable_self_register must be disabled in production")
            if self.langfuse_enabled:
                if not self.langfuse_public_key or not self.langfuse_secret_key:
                    raise ValueError(
                        "langfuse_public_key and langfuse_secret_key are required when langfuse_enabled=true"
                    )
        return self


settings = Settings()
