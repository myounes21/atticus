import uuid
from typing import Any, cast
from types import SimpleNamespace

from backend.ingestion.detection.doc_type_detector import DetectionResult
from backend.ingestion.errors import IngestionStage, IngestionStageError
from backend.ingestion.pipeline import IngestionResult
from backend.schemas.chunkers_schema import Chunk
from backend.schemas.parsed_document import ParsedDocument
from backend.tasks.ingest_task import IngestionJobStatus, ingest_document, ingest_document_task


class _FakeJobStore:
    def __init__(self) -> None:
        self.status_history: list[str] = []
        self.rows: dict[str, object] = {}

    def create_job(self, *, file_id: uuid.UUID, file_path: str, status: str = "queued"):
        self.status_history = [status]
        self.rows = {
            "file_id": file_id,
            "file_path": file_path,
            "status": status,
            "needs_review": False,
            "indexed": False,
            "failed_stage": None,
            "error": None,
        }

    def update_job(self, *, file_id: uuid.UUID, status: str, **kwargs):
        self.status_history.append(status)
        self.rows.update(kwargs)
        self.rows["status"] = status


def test_ingest_document_returns_completed(monkeypatch) -> None:
    file_id = uuid.uuid4()
    store = _FakeJobStore()
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

    result = ingest_document(file_path="/tmp/doc.txt", file_id=file_id, job_store=cast(Any, store))

    assert result.file_id == file_id
    assert result.status == IngestionJobStatus.COMPLETED
    assert result.needs_review is False
    assert result.category == "note"
    assert result.indexed is True
    assert result.status_history == ["queued", "running", "indexing", "completed"]
    assert elastic_calls["count"] == 1
    assert qdrant_calls["count"] == 1
    assert store.rows["status"] == "completed"
    assert store.rows["indexed"] is True


def test_ingest_document_returns_review_required(monkeypatch) -> None:
    file_id = uuid.uuid4()
    store = _FakeJobStore()

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

    result = ingest_document(file_path="/tmp/doc.txt", file_id=file_id, job_store=cast(Any, store))

    assert result.status == IngestionJobStatus.REVIEW_REQUIRED
    assert result.needs_review is True
    assert result.indexed is False
    assert result.status_history == ["queued", "running", "review_required"]
    assert store.rows["status"] == "review_required"
    assert store.rows["needs_review"] is True


def test_ingest_document_returns_failed_on_stage_error(monkeypatch) -> None:
    store = _FakeJobStore()

    def _raise_stage_error(**kwargs):
        raise IngestionStageError(
            stage=IngestionStage.DETECT,
            message="boom",
            cause=ValueError("bad"),
        )

    monkeypatch.setattr("backend.tasks.ingest_task.run_pipeline", _raise_stage_error)

    result = ingest_document(file_path="/tmp/doc.txt", job_store=cast(Any, store))

    assert result.status == IngestionJobStatus.FAILED
    assert result.failed_stage == "detect"
    assert result.error is not None
    assert result.status_history == ["queued", "running", "failed"]
    assert store.rows["status"] == "failed"
    assert store.rows["failed_stage"] == "detect"


def test_ingest_document_returns_failed_when_indexing_fails(monkeypatch) -> None:
    file_id = uuid.uuid4()
    store = _FakeJobStore()
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

    result = ingest_document(file_path="/tmp/doc.txt", file_id=file_id, job_store=cast(Any, store))

    assert result.status == IngestionJobStatus.FAILED
    assert result.failed_stage == "index"
    assert "qdrant down" in (result.error or "")
    assert result.status_history == ["queued", "running", "indexing", "failed"]
    assert store.rows["status"] == "failed"
    assert store.rows["failed_stage"] == "index"


def test_ingest_document_task_uses_precreated_job_mode(monkeypatch) -> None:
    file_id = uuid.uuid4()
    case_id = uuid.uuid4()
    lawyer_id = uuid.uuid4()
    captured: dict[str, object] = {}

    def _fake_ingest_document(**kwargs):
        captured.update(kwargs)
        return SimpleNamespace(file_id=kwargs["file_id"], status=IngestionJobStatus.COMPLETED)

    monkeypatch.setattr("backend.tasks.ingest_task.ingest_document", _fake_ingest_document)

    result = ingest_document_task(
        file_id=str(file_id),
        file_path="/tmp/test.txt",
        case_id=str(case_id),
        case_name="Case A",
        assigned_lawyers=[str(lawyer_id)],
        version=2,
    )

    assert result == {"file_id": str(file_id), "status": "completed"}
    assert captured["create_job_if_missing"] is False
    assert captured["case_id"] == case_id
    assert captured["assigned_lawyers"] == [lawyer_id]


def test_ingest_document_falls_back_to_local_when_s3_download_fails(
    monkeypatch,
    tmp_path,
) -> None:
    file_id = uuid.uuid4()
    store = _FakeJobStore()
    local_path = tmp_path / "doc.txt"
    local_path.write_text("hello", encoding="utf-8")
    captured_pipeline: dict[str, object] = {}

    def _fake_pipeline(**kwargs):
        captured_pipeline.update(kwargs)
        return IngestionResult(
            file_id=file_id,
            file_type="txt",
            detection=DetectionResult(
                category="note",
                structure_type="unstructured",
                needs_review=False,
            ),
            parsed_document=ParsedDocument(text="hello"),
            chunks=[],
            needs_review=False,
            stage_timings_ms={"parse": 1},
        )

    monkeypatch.setattr(
        "backend.tasks.ingest_task.s3_download_file",
        lambda **kwargs: (_ for _ in ()).throw(RuntimeError("s3 down")),
    )
    monkeypatch.setattr("backend.tasks.ingest_task.run_pipeline", _fake_pipeline)

    result = ingest_document(
        file_path=str(local_path),
        file_id=file_id,
        s3_key="documents/case/file/doc.txt",
        file_name="doc.txt",
        job_store=cast(Any, store),
    )

    assert result.status == IngestionJobStatus.COMPLETED
    assert str(captured_pipeline["file_path"]) == str(local_path)


