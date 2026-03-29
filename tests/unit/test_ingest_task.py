import uuid

from backend.ingestion.detection.doc_type_detector import DetectionResult
from backend.ingestion.errors import IngestionStage, IngestionStageError
from backend.ingestion.pipeline import IngestionResult
from backend.schemas.parsed_document import ParsedDocument
from backend.tasks.ingest_task import IngestionJobStatus, ingest_document


def test_ingest_document_returns_completed(monkeypatch) -> None:
    file_id = uuid.uuid4()

    monkeypatch.setattr(
        "backend.tasks.ingest_task.run_pipeline",
        lambda **kwargs: IngestionResult(
            file_id=file_id,
            file_type="txt",
            detection=DetectionResult(category="note", structure_type="unstructured", needs_review=False),
            parsed_document=ParsedDocument(text="hello"),
            chunks=[],
            needs_review=False,
            stage_timings_ms={"parse": 3, "detect": 2},
        ),
    )

    result = ingest_document(file_path="/tmp/doc.txt", file_id=file_id)

    assert result.file_id == file_id
    assert result.status == IngestionJobStatus.COMPLETED
    assert result.needs_review is False
    assert result.category == "note"


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

