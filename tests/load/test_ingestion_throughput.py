import time
import uuid
import logging
from pathlib import Path
from backend.tasks.ingest_task import ingest_document
from backend.db.postgres import execute_returning_one, fetch_optional
import psycopg
from config import settings
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parents[2]
DEMO_DATA_DIR = BASE_DIR / "backend" / "demo_data"

def create_benchmark_case() -> uuid.UUID:
    """Create a temporary case to isolate the benchmarking metrics."""
    # Ensure an admin user exists
    user_row = execute_returning_one(
        """
        INSERT INTO users (user_id, email, password_hash, role, full_name)
        VALUES (%s, 'benchmark@atticus.local', 'hash', 'admin', 'Benchmark User')
        ON CONFLICT (email) DO UPDATE SET email=EXCLUDED.email
        RETURNING user_id
        """,
        (uuid.uuid4(),)
    )
    user_id = user_row["user_id"]
    
    case_id = uuid.uuid4()
    execute_returning_one(
        """
        INSERT INTO cases (case_id, name, client_name, status, created_by, assigned_lawyers)
        VALUES (%s, 'Ingestion Benchmark', 'Benchmark Client', 'active', %s, %s::uuid[])
        RETURNING case_id
        """,
        (case_id, user_id, [user_id])
    )
    return case_id

def run_ingestion_throughput_test():
    files = list(DEMO_DATA_DIR.rglob("*.txt")) + list(DEMO_DATA_DIR.rglob("*.pdf")) + list(DEMO_DATA_DIR.rglob("*.docx"))
    
    if not files:
        logger.error("No files found to ingest in demo data/.")
        return

    logger.info(f"Setting up benchmark case...")
    case_id = create_benchmark_case()

    logger.info(f"Starting synchronous ingestion of {len(files)} files...")
    start_time = time.time()
    
    for i, file_path in enumerate(files):
        logger.info(f"Ingesting {i+1}/{len(files)}: {file_path.name}")
        file_id = uuid.uuid4()
        
        # We need to register the document in Postgres first so the ingestion pipeline can update it
        execute_returning_one(
            """
            INSERT INTO documents (file_id, case_id, name, version, is_latest, status, uploaded_by)
            VALUES (%s, %s, %s, 1, TRUE, 'processing', (SELECT created_by FROM cases WHERE case_id = %s))
            RETURNING file_id
            """,
            (file_id, case_id, file_path.name, case_id)
        )
        
        # Call the ingestion pipeline (Parsing -> Chunking -> Embedding -> Indexing)
        try:
            ingest_document(
                file_path=file_path,
                file_id=file_id,
                file_name=file_path.name,
                document_name=file_path.name,
                case_id=case_id,
                case_name="Ingestion Benchmark",
                assigned_lawyers=[],
                version=1,
            )
        except Exception as e:
            logger.error(f"Failed to ingest {file_path.name}: {e}")
        
    end_time = time.time()
    total_time = end_time - start_time
    
    # Calculate Metrics
    # Count the total number of chunks produced for this case
    row = fetch_optional("SELECT COALESCE(SUM(chunk_count), 0) as total_chunks FROM ingestion_jobs WHERE file_id IN (SELECT file_id FROM documents WHERE case_id = %s)", (case_id,))
    total_chunks = row["total_chunks"] if row else 0
    
    # Estimate total pages (approx 500 words or 2.5 chunks per page)
    # This is a rough estimation used in standard NLP benchmarking
    total_pages = total_chunks / 2.5
    
    chunks_per_sec = total_chunks / total_time if total_time > 0 else 0
    pages_per_min = (total_pages / total_time) * 60 if total_time > 0 else 0
    
    print("\n" + "="*50)
    print("INGESTION THROUGHPUT RESULTS")
    print("="*50)
    print(f"Total Files Ingested: {len(files)}")
    print(f"Total Chunks Created: {total_chunks}")
    print(f"Estimated Pages:      {total_pages:.1f}")
    print(f"Total Time:           {total_time:.2f} seconds")
    print("-" * 50)
    print(f"Throughput (Chunks):  {chunks_per_sec:.2f} chunks / second")
    print(f"Throughput (Pages):   {pages_per_min:.2f} pages / minute")
    print("="*50)

if __name__ == "__main__":
    run_ingestion_throughput_test()
