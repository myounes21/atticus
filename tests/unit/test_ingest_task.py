import uuid

from backend.ingestion.detection.doc_type_detector import DetectionResult
from backend.ingestion.errors import IngestionStage, IngestionStageError
from backend.ingestion.pipeline import IngestionResult
from backend.schemas.chunkers_schema import Chunk
from backend.schemas.parsed_document import ParsedDocument
from backend.tasks.ingest_task import IngestionJobStatus, ingest_document


def test_ingest_document_returns_completed(monkeypatch) -> None:
    file_id = uuid.uuid4()
    chunk = Chunk(
        text="hello world",
        chunk_index=0,
        file_type="txt",
        document_type="note",
        document_name="doc.txt",
    )

    elastic_calls = {"count": 0}
    qdrant_calls = {"count": 0}

    monkeypatch.setattr(
        "backend.tasks.ingest_task.run_pipeline",
        lambda **kwargs: IngestionResult(
            file_id=file_id,
            file_type="txt",
            detection=DetectionResult(category="note", structure_type="unstructured", needs_review=False),
            parsed_document=ParsedDocument(text="hello"),
            chunks=[chunk],
            needs_review=False,
            stage_timings_ms={"parse": 3, "detect": 2},
        ),
    )
    monkeypatch.setattr("backend.tasks.ingest_task.embed_texts", lambda texts: [[0.1, 0.2]])
    monkeypatch.setattr(
        "backend.tasks.ingest_task.index_chunks_elastic",
        lambda chunks: elastic_calls.__setitem__("count", elastic_calls["count"] + 1),
    )
    monkeypatch.setattr(
        "backend.tasks.ingest_task.index_chunks_qdrant",
        lambda chunks, vectors: qdrant_calls.__setitem__("count", qdrant_calls["count"] + 1),
    )

    result = ingest_document(file_path="/tmp/doc.txt", file_id=file_id)

    assert result.file_id == file_id
    assert result.status == IngestionJobStatus.COMPLETED
    assert result.needs_review is False
    assert result.category == "note"
    assert result.indexed is True
    assert result.status_history == ["queued", "running", "indexing", "completed"]
    assert elastic_calls["count"] == 1
    assert qdrant_calls["count"] == 1


def test_ingest_document_returns_review_required(monkeypatch) -> None:
    file_id = uuid.uuid4()

    monkeypatch.setattr(
        "backend.tasks.ingest_task.run_pipeline",
        lambda **kwargs: IngestionResult(
            file_id=file_id,
            file_type="txt",
            detection=DetectionResult(category="unknown", structure_type="unstructured", needs_review=True),
            parsed_document=ParsedDocument(text="garbage"),
            chunks=[],
            needs_review=True,
            stage_timings_ms={"parse": 3, "detect": 2},
        ),
    )

    result = ingest_document(file_path="/tmp/doc.txt", file_id=file_id)

    assert result.status == IngestionJobStatus.REVIEW_REQUIRED
    assert result.needs_review is True
    assert result.indexed is False
    assert result.status_history == ["queued", "running", "review_required"]


def test_ingest_document_returns_failed_on_stage_error(monkeypatch) -> None:
    def _raise_stage_error(**kwargs):
        raise IngestionStageError(
            stage=IngestionStage.DETECT,
            message="boom",
            cause=ValueError("bad"),
        )

    monkeypatch.setattr("backend.tasks.ingest_task.run_pipeline", _raise_stage_error)

    result = ingest_document(file_path="/tmp/doc.txt")

    assert result.status == IngestionJobStatus.FAILED
    assert result.failed_stage == "detect"
    assert result.error is not None
    assert result.status_history == ["queued", "running", "failed"]


def test_ingest_document_returns_failed_when_indexing_fails(monkeypatch) -> None:
    file_id = uuid.uuid4()
    chunk = Chunk(
        text="hello world",
        chunk_index=0,
        file_type="txt",
        document_type="note",
        document_name="doc.txt",
    )

    monkeypatch.setattr(
        "backend.tasks.ingest_task.run_pipeline",
        lambda **kwargs: IngestionResult(
            file_id=file_id,
            file_type="txt",
            detection=DetectionResult(category="note", structure_type="unstructured", needs_review=False),
            parsed_document=ParsedDocument(text="hello"),
            chunks=[chunk],
            needs_review=False,
            stage_timings_ms={"parse": 3, "detect": 2},
        ),
    )
    monkeypatch.setattr("backend.tasks.ingest_task.embed_texts", lambda texts: [[0.1, 0.2]])
    monkeypatch.setattr("backend.tasks.ingest_task.index_chunks_elastic", lambda chunks: None)
    monkeypatch.setattr(
        "backend.tasks.ingest_task.index_chunks_qdrant",
        lambda chunks, vectors: (_ for _ in ()).throw(RuntimeError("qdrant down")),
    )

    result = ingest_document(file_path="/tmp/doc.txt", file_id=file_id)

    assert result.status == IngestionJobStatus.FAILED
    assert result.failed_stage == "index"
    assert "qdrant down" in (result.error or "")
    assert result.status_history == ["queued", "running", "indexing", "failed"]

