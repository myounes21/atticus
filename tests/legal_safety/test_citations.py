import uuid

from backend.api.routes.chat import _build_chunk_refs


def test_build_chunk_refs_preserves_ids_and_metadata() -> None:
    chunk_id = uuid.uuid4()
    file_id = uuid.uuid4()

    refs = _build_chunk_refs(
        [
            {
                "chunk_id": str(chunk_id),
                "file_id": str(file_id),
                "document_name": "brief.txt",
                "document_type": "brief",
                "score": 0.87,
            }
        ]
    )

    assert len(refs) == 1
    assert refs[0].chunk_id == chunk_id
    assert refs[0].file_id == file_id
    assert refs[0].document_name == "brief.txt"
    assert refs[0].document_type == "brief"
    assert refs[0].score == 0.87


def test_build_chunk_refs_generates_chunk_id_when_missing() -> None:
    refs = _build_chunk_refs([{"file_id": None, "document_name": "note.txt"}])

    assert len(refs) == 1
    assert isinstance(refs[0].chunk_id, uuid.UUID)
    assert refs[0].file_id is None

