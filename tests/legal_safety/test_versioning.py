import uuid

from backend.ingestion.detection.doc_type_detector import DetectionResult
from backend.ingestion.pipeline import run_pipeline
from backend.schemas.chunkers_schema import Chunk
from backend.schemas.parsed_document import ParsedDocument


class _FakeParser:
    def parse(self, _file_path):
        return ParsedDocument(text="sample text")


class _FakeChunker:
    def chunk(self, _parsed_document):
        return [
            Chunk(
                text="chunk text",
                chunk_index=0,
                file_type="txt",
                document_type="note",
                document_name="doc.txt",
            )
        ]


def test_pipeline_assigns_version_and_latest_flag(monkeypatch) -> None:
    monkeypatch.setattr("backend.ingestion.pipeline.get_file_extension", lambda _path: "txt")
    monkeypatch.setattr("backend.ingestion.pipeline.get_parser", lambda _ft: _FakeParser())
    monkeypatch.setattr(
        "backend.ingestion.pipeline.detect",
        lambda content, file_type: DetectionResult(
            category="note",
            structure_type="unstructured",
            needs_review=False,
        ),
    )
    monkeypatch.setattr("backend.ingestion.pipeline.get_chunker", lambda _category: _FakeChunker())
    monkeypatch.setattr(
        "backend.ingestion.pipeline.enrich_chunks",
        lambda chunks, case_name=None: chunks,
    )

    result = run_pipeline(
        file_path="/tmp/example.txt",
        file_id=uuid.uuid4(),
        case_id=uuid.uuid4(),
        assigned_lawyers=[uuid.uuid4()],
        version=7,
    )

    assert len(result.chunks) == 1
    assert result.chunks[0].version == 7
    assert result.chunks[0].is_latest is True

