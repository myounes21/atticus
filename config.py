from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

ENV_PATH = Path(__file__).resolve().parent / ".env"

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ENV_PATH, extra="ignore")

    groq_api_key: str
    groq_llm_model: str = "llama-3.3-70b-versatile"

    # document detector configs
    detection_snippet_length: int = 1000

    # Chunking configs
    CHUNK_SIZE_MIN = 300
    CHUNK_SIZE_MAX = 500
    CHUNK_OVERLAP = 50

    # Embedder
    embedder_model: str = "BAAI/bge-m3"
    embedding_dimension: int = 1024


    # Reranker (HuggingFace only)
    huggingface_reranker_model: str = "BAAI/bge-reranker-base"


    # Qdrant
    qdrant_host: str
    qdrant_port: int
    qdrant_collection_name: str = "chunks"

    # Elasticsearch
    elasticsearch_host: str
    elasticsearch_port: int
    elasticsearch_password: str = ""
    elasticsearch_index_name: str = "chunks"

    # Redis
    redis_host: str
    redis_port: int

    # Langfuse
    langfuse_public_key: str
    langfuse_secret_key: str
    langfuse_host: str
    langfuse_port: int

    # retrieve pipline
    retrieval_top_k : int = 12
    rrf_top_k: int = 10
    rerank_top_k: int = 3

    app_port: int = 8000

    app_env: str = "development"

settings = Settings()