import uuid

from backend.db.postgres import IngestionJobStore


def test_job_store_create_and_get(tmp_path) -> None:
    store = IngestionJobStore(db_path=tmp_path / "jobs.db")
    file_id = uuid.uuid4()

    store.create_job(file_id=file_id, file_path="/tmp/doc.txt", status="queued")
    row = store.get_job(file_id)

    assert row.file_id == file_id
    assert row.file_path == "/tmp/doc.txt"
    assert row.status == "queued"
    assert row.status_history == ["queued"]
    assert row.indexed is False


def test_job_store_update_appends_history_and_fields(tmp_path) -> None:
    store = IngestionJobStore(db_path=tmp_path / "jobs.db")
    file_id = uuid.uuid4()

    store.create_job(file_id=file_id, file_path="/tmp/doc.txt", status="queued")
    store.update_job(
        file_id=file_id,
        status="running",
        stage_timings_ms={"parse": 5},
    )
    store.update_job(
        file_id=file_id,
        status="completed",
        category="note",
        structure_type="unstructured",
        chunk_count=2,
        indexed=True,
    )

    row = store.get_job(file_id)
    assert row.status == "completed"
    assert row.status_history == ["queued", "running", "completed"]
    assert row.stage_timings_ms == {"parse": 5}
    assert row.category == "note"
    assert row.structure_type == "unstructured"
    assert row.chunk_count == 2
    assert row.indexed is True

