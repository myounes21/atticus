import uuid

import pytest

from backend.ingestion.errors import IngestionStage, IngestionStageError
from backend.ingestion.pipeline import run_pipeline
from backend.ingestion.detection.doc_type_detector import DetectionResult
from backend.schemas.chunkers_schema import Chunk
from backend.schemas.parsed_document import Metadata, ParsedDocument


class _StubParser:
    def __init__(self, parsed_document: ParsedDocument) -> None:
        self._parsed_document = parsed_document

    def parse(self, file_path):
        return self._parsed_document


class _StubChunker:
    def __init__(self, chunks: list[Chunk]) -> None:
        self._chunks = chunks

    def chunk(self, document: ParsedDocument):
        return self._chunks


def test_run_pipeline_records_timings_and_assigns_chunk_fields(monkeypatch) -> None:
    parsed = ParsedDocument(
        text="hello world",
        metadata=Metadata(document_name="doc.txt", file_type="txt"),
    )
    base_chunk = Chunk(
        text="chunk text",
        chunk_index=0,
        file_type="txt",
        document_type="note",
        document_name="doc.txt",
    )

    monkeypatch.setattr("backend.ingestion.pipeline.get_file_extension", lambda path: "txt")
    monkeypatch.setattr("backend.ingestion.pipeline.get_parser", lambda file_type: _StubParser(parsed))
    monkeypatch.setattr(
        "backend.ingestion.pipeline.detect",
        lambda text, file_type: DetectionResult(category="note", structure_type="unstructured", needs_review=False),
    )
    monkeypatch.setattr("backend.ingestion.pipeline.get_chunker", lambda category: _StubChunker([base_chunk]))
    monkeypatch.setattr("backend.ingestion.pipeline.enrich_chunks", lambda chunks, case_name=None: chunks)

    file_id = uuid.uuid4()
    case_id = uuid.uuid4()
    lawyer_id = uuid.uuid4()

    result = run_pipeline(
        file_path="/tmp/doc.txt",
        file_id=file_id,
        case_id=case_id,
        case_name="Case A",
        assigned_lawyers=[lawyer_id],
        version=3,
    )

    assert result.needs_review is False
    assert result.stage_timings_ms is not None
    assert set(result.stage_timings_ms).issuperset({"file_type", "parse", "detect", "chunk", "enrich"})
    assert len(result.chunks) == 1
    assert result.chunks[0].file_id == file_id
    assert result.chunks[0].case_id == case_id
    assert result.chunks[0].assigned_lawyers == [lawyer_id]
    assert result.chunks[0].version == 3


def test_run_pipeline_raises_stage_error_on_parse_failure(monkeypatch) -> None:
    class _FailingParser:
        def parse(self, file_path):
            raise ValueError("bad parse")

    monkeypatch.setattr("backend.ingestion.pipeline.get_file_extension", lambda path: "txt")
    monkeypatch.setattr("backend.ingestion.pipeline.get_parser", lambda file_type: _FailingParser())

    with pytest.raises(IngestionStageError) as exc:
        run_pipeline(file_path="/tmp/doc.txt")

    assert exc.value.stage == IngestionStage.PARSE
    assert "bad parse" in str(exc.value)


def test_run_pipeline_short_circuits_on_review(monkeypatch) -> None:
    parsed = ParsedDocument(
        text="unclear",
        metadata=Metadata(document_name="doc.txt", file_type="txt"),
    )

    monkeypatch.setattr("backend.ingestion.pipeline.get_file_extension", lambda path: "txt")
    monkeypatch.setattr("backend.ingestion.pipeline.get_parser", lambda file_type: _StubParser(parsed))
    monkeypatch.setattr(
        "backend.ingestion.pipeline.detect",
        lambda text, file_type: DetectionResult(category="unknown", structure_type="unstructured", needs_review=True),
    )

    result = run_pipeline(file_path="/tmp/doc.txt")

    assert result.needs_review is True
    assert result.chunks == []
    assert result.stage_timings_ms is not None
    assert set(result.stage_timings_ms).issuperset({"file_type", "parse", "detect"})
    assert "chunk" not in result.stage_timings_ms

