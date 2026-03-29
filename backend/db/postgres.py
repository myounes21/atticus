import json
import sqlite3
import threading
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


def _utc_now_iso() -> str:
	return datetime.now(timezone.utc).isoformat()


@dataclass(slots=True)
class IngestionJobRecord:
	file_id: uuid.UUID
	file_path: str
	status: str
	needs_review: bool
	category: str | None
	structure_type: str | None
	chunk_count: int
	indexed: bool
	status_history: list[str]
	stage_timings_ms: dict[str, int] | None
	failed_stage: str | None
	error: str | None
	created_at: str
	updated_at: str


class IngestionJobStore:
	"""Simple SQLite-backed job store used by ingestion task orchestration."""

	def __init__(self, db_path: str | Path | None = None) -> None:
		if db_path is None:
			db_path = Path(__file__).resolve().parents[2] / "atticus.db"
		self._db_path = Path(db_path)
		self._lock = threading.Lock()
		self._init_db()

	def _connect(self) -> sqlite3.Connection:
		conn = sqlite3.connect(self._db_path)
		conn.row_factory = sqlite3.Row
		return conn

	def _init_db(self) -> None:
		with self._connect() as conn:
			conn.execute(
				"""
				CREATE TABLE IF NOT EXISTS ingestion_jobs (
					file_id TEXT PRIMARY KEY,
					file_path TEXT NOT NULL,
					status TEXT NOT NULL,
					needs_review INTEGER NOT NULL DEFAULT 0,
					category TEXT,
					structure_type TEXT,
					chunk_count INTEGER NOT NULL DEFAULT 0,
					indexed INTEGER NOT NULL DEFAULT 0,
					status_history TEXT NOT NULL,
					stage_timings_ms TEXT,
					failed_stage TEXT,
					error TEXT,
					created_at TEXT NOT NULL,
					updated_at TEXT NOT NULL
				)
				"""
			)

	def create_job(
		self,
		*,
		file_id: uuid.UUID,
		file_path: str,
		status: str = "queued",
	) -> IngestionJobRecord:
		created_at = _utc_now_iso()
		status_history = [status]
		with self._lock, self._connect() as conn:
			conn.execute(
				"""
				INSERT OR REPLACE INTO ingestion_jobs (
					file_id,
					file_path,
					status,
					needs_review,
					category,
					structure_type,
					chunk_count,
					indexed,
					status_history,
					stage_timings_ms,
					failed_stage,
					error,
					created_at,
					updated_at
				) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
				""",
				(
					str(file_id),
					file_path,
					status,
					0,
					None,
					None,
					0,
					0,
					json.dumps(status_history),
					None,
					None,
					None,
					created_at,
					created_at,
				),
			)

		return self.get_job(file_id)

	def update_job(
		self,
		*,
		file_id: uuid.UUID,
		status: str,
		append_history: bool = True,
		needs_review: bool | None = None,
		category: str | None = None,
		structure_type: str | None = None,
		chunk_count: int | None = None,
		indexed: bool | None = None,
		stage_timings_ms: dict[str, int] | None = None,
		failed_stage: str | None = None,
		error: str | None = None,
	) -> IngestionJobRecord:
		with self._lock, self._connect() as conn:
			row = conn.execute(
				"SELECT * FROM ingestion_jobs WHERE file_id = ?",
				(str(file_id),),
			).fetchone()
			if row is None:
				raise ValueError(f"Job not found for file_id '{file_id}'")

			current_history = json.loads(row["status_history"])
			if append_history:
				current_history.append(status)

			next_needs_review = int(bool(row["needs_review"])) if needs_review is None else int(bool(needs_review))
			next_category = row["category"] if category is None else category
			next_structure = row["structure_type"] if structure_type is None else structure_type
			next_chunk_count = int(row["chunk_count"]) if chunk_count is None else int(chunk_count)
			next_indexed = int(bool(row["indexed"])) if indexed is None else int(bool(indexed))
			next_stage_timings = row["stage_timings_ms"]
			if stage_timings_ms is not None:
				next_stage_timings = json.dumps(stage_timings_ms)
			next_failed_stage = row["failed_stage"] if failed_stage is None else failed_stage
			next_error = row["error"] if error is None else error

			conn.execute(
				"""
				UPDATE ingestion_jobs
				   SET status = ?,
					   needs_review = ?,
					   category = ?,
					   structure_type = ?,
					   chunk_count = ?,
					   indexed = ?,
					   status_history = ?,
					   stage_timings_ms = ?,
					   failed_stage = ?,
					   error = ?,
					   updated_at = ?
				 WHERE file_id = ?
				""",
				(
					status,
					next_needs_review,
					next_category,
					next_structure,
					next_chunk_count,
					next_indexed,
					json.dumps(current_history),
					next_stage_timings,
					next_failed_stage,
					next_error,
					_utc_now_iso(),
					str(file_id),
				),
			)

		return self.get_job(file_id)

	def get_job(self, file_id: uuid.UUID) -> IngestionJobRecord:
		with self._connect() as conn:
			row = conn.execute(
				"SELECT * FROM ingestion_jobs WHERE file_id = ?",
				(str(file_id),),
			).fetchone()

		if row is None:
			raise ValueError(f"Job not found for file_id '{file_id}'")

		stage_timings_ms = None
		if row["stage_timings_ms"]:
			stage_timings_ms = json.loads(row["stage_timings_ms"])

		return IngestionJobRecord(
			file_id=uuid.UUID(row["file_id"]),
			file_path=row["file_path"],
			status=row["status"],
			needs_review=bool(row["needs_review"]),
			category=row["category"],
			structure_type=row["structure_type"],
			chunk_count=int(row["chunk_count"]),
			indexed=bool(row["indexed"]),
			status_history=list(json.loads(row["status_history"])),
			stage_timings_ms=stage_timings_ms,
			failed_stage=row["failed_stage"],
			error=row["error"],
			created_at=row["created_at"],
			updated_at=row["updated_at"],
		)


_JOB_STORE: IngestionJobStore | None = None


def get_ingestion_job_store() -> IngestionJobStore:
	global _JOB_STORE
	if _JOB_STORE is None:
		_JOB_STORE = IngestionJobStore()
	return _JOB_STORE

