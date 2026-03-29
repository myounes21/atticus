from fastapi import FastAPI

from backend.api.routes.ingestion import router as ingestion_router


app = FastAPI(title="Atticus API")
app.include_router(ingestion_router)

