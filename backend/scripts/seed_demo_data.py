"""Seed deterministic demo users, cases, and synthetic documents.

Designed for CV/demo environments where reviewers should see a fully working
flow immediately after login.
"""

from __future__ import annotations

import uuid
from pathlib import Path

from backend.core.security import hash_password
from backend.db.postgres import execute, execute_returning_one, fetch_optional
from backend.tasks.ingest_task import ingest_document

BASE_DIR = Path(__file__).resolve().parents[1]
DEMO_DOCS_DIR = BASE_DIR / "demo_data"
UPLOAD_TMP_DIR = Path("/tmp/atticus_uploads")

ADMIN_EMAIL = "demo.admin@atticus.local"
LAWYER_EMAIL = "demo.lawyer@atticus.local"
DEMO_PASSWORD = "DemoPass!123"


def _ensure_user(email: str, role: str) -> uuid.UUID:
    row = fetch_optional("SELECT user_id, role FROM users WHERE email = %s", (email,))
    if row is not None:
        if row["role"] != role:
            execute(
                "UPDATE users SET role = %s WHERE user_id = %s", (role, row["user_id"])
            )
        return row["user_id"]

    created = execute_returning_one(
        """
        INSERT INTO users (user_id, email, password_hash, role)
        VALUES (%s, %s, %s, %s)
        RETURNING user_id
        """,
        (uuid.uuid4(), email, hash_password(DEMO_PASSWORD), role),
    )
    return created["user_id"]


def _ensure_case(
    *,
    name: str,
    client_name: str,
    created_by: uuid.UUID,
    assigned_lawyer_id: uuid.UUID,
) -> uuid.UUID:
    row = fetch_optional("SELECT case_id FROM cases WHERE name = %s", (name,))
    if row is not None:
        execute(
            "UPDATE cases SET client_name = %s, assigned_lawyers = %s::uuid[] WHERE case_id = %s",
            (client_name, [assigned_lawyer_id], row["case_id"]),
        )
        return row["case_id"]

    created = execute_returning_one(
        """
        INSERT INTO cases (case_id, name, client_name, status, closed_at, created_by, assigned_lawyers)
        VALUES (%s, %s, %s, 'active', NULL, %s, %s::uuid[])
        RETURNING case_id
        """,
        (uuid.uuid4(), name, client_name, created_by, [assigned_lawyer_id]),
    )
    return created["case_id"]


def _ensure_document(
    *,
    case_id: uuid.UUID,
    uploaded_by: uuid.UUID,
    file_name: str,
    source_path: Path,
) -> None:
    existing = fetch_optional(
        "SELECT file_id, status FROM documents WHERE case_id = %s AND name = %s AND is_latest = TRUE",
        (case_id, file_name),
    )
    if existing is not None:
        if existing["status"] == "ready":
            return
        temp_path = UPLOAD_TMP_DIR / f"{existing['file_id']}_{file_name}"
        UPLOAD_TMP_DIR.mkdir(parents=True, exist_ok=True)
        temp_path.write_text(source_path.read_text(encoding="utf-8"), encoding="utf-8")
        ingest_document(
            file_path=temp_path,
            file_id=existing["file_id"],
            case_id=case_id,
            case_name=file_name,
            assigned_lawyers=_assigned_lawyers_for_case(case_id),
            version=1,
        )
        return

    file_id = uuid.uuid4()
    execute_returning_one(
        """
        INSERT INTO documents (file_id, case_id, name, version, is_latest, status, s3_key, uploaded_by)
        VALUES (%s, %s, %s, 1, TRUE, 'processing', NULL, %s)
        RETURNING file_id
        """,
        (file_id, case_id, file_name, uploaded_by),
    )

    temp_path = UPLOAD_TMP_DIR / f"{file_id}_{file_name}"
    UPLOAD_TMP_DIR.mkdir(parents=True, exist_ok=True)
    temp_path.write_text(source_path.read_text(encoding="utf-8"), encoding="utf-8")

    ingest_document(
        file_path=temp_path,
        file_id=file_id,
        case_id=case_id,
        case_name=file_name,
        assigned_lawyers=_assigned_lawyers_for_case(case_id),
        version=1,
    )


def _assigned_lawyers_for_case(case_id: uuid.UUID) -> list[uuid.UUID]:
    case_row = fetch_optional(
        "SELECT assigned_lawyers FROM cases WHERE case_id = %s",
        (case_id,),
    )
    return list(case_row["assigned_lawyers"] or []) if case_row else []


def main() -> None:
    for required in (
        DEMO_DOCS_DIR / "acme_master_service_terms.txt",
        DEMO_DOCS_DIR / "acme_incident_timeline.txt",
        DEMO_DOCS_DIR / "greenfield_lease_dispute_brief.txt",
    ):
        if not required.exists():
            raise FileNotFoundError(f"Missing demo document: {required}")

    admin_id = _ensure_user(ADMIN_EMAIL, "admin")
    lawyer_id = _ensure_user(LAWYER_EMAIL, "lawyer")

    acme_case_id = _ensure_case(
        name="Acme Logistics Breach Response",
        client_name="Acme Logistics",
        created_by=admin_id,
        assigned_lawyer_id=lawyer_id,
    )
    greenfield_case_id = _ensure_case(
        name="Greenfield Lease Dispute",
        client_name="Greenfield Holdings",
        created_by=admin_id,
        assigned_lawyer_id=lawyer_id,
    )

    _ensure_document(
        case_id=acme_case_id,
        uploaded_by=admin_id,
        file_name="acme_master_service_terms.txt",
        source_path=DEMO_DOCS_DIR / "acme_master_service_terms.txt",
    )
    _ensure_document(
        case_id=acme_case_id,
        uploaded_by=admin_id,
        file_name="acme_incident_timeline.txt",
        source_path=DEMO_DOCS_DIR / "acme_incident_timeline.txt",
    )
    _ensure_document(
        case_id=greenfield_case_id,
        uploaded_by=admin_id,
        file_name="greenfield_lease_dispute_brief.txt",
        source_path=DEMO_DOCS_DIR / "greenfield_lease_dispute_brief.txt",
    )


if __name__ == "__main__":
    main()
