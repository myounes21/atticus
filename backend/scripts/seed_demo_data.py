import uuid
import re
from pathlib import Path

from backend.core.security import hash_password
from backend.db.postgres import execute, execute_returning_one, fetch_optional
from backend.tasks.ingest_task import ingest_document

BASE_DIR = Path(__file__).resolve().parents[1]
DEMO_DOCS_DIR = BASE_DIR / "demo_data"
ROOT_DEMO_DOCS_DIR = BASE_DIR.parent / "demo data"
UPLOAD_TMP_DIR = Path("/tmp/atticus_uploads")

ADMIN_EMAIL = "demo.admin@atticus.local"
LAWYER_EMAIL = "demo.lawyer@atticus.local"
LAWYER_TWO_EMAIL = "maria.rossi@atticus.local"
LAWYER_THREE_EMAIL = "james.carter@atticus.local"
DEMO_PASSWORD = "DemoPass!123"
ALLOWED_DEMO_SUFFIXES = {".pdf", ".docx", ".txt", ".eml"}

DISPLAY_NAMES: dict[str, str] = {
    ADMIN_EMAIL: "Admin Finch",
    LAWYER_EMAIL: "Mr Lawyer",
    LAWYER_TWO_EMAIL: "Maria Rossi",
    LAWYER_THREE_EMAIL: "James Carter",
}

_UPPER_WORDS = {"nda", "ip", "ai", "api", "llm", "it", "ceo", "vp"}


def _humanize_file_name(file_name: str) -> str:
    path = Path(file_name)
    stem = path.stem
    ext = path.suffix.lower()
    words = [part for part in re.split(r"[_\-]+", stem) if part]
    if not words:
        return file_name

    formatted_words: list[str] = []
    for word in words:
        lowered = word.lower()
        if lowered in _UPPER_WORDS:
            formatted_words.append(lowered.upper())
        elif lowered.isdigit():
            formatted_words.append(lowered)
        else:
            formatted_words.append(lowered.capitalize())

    return f"{' '.join(formatted_words)}{ext}"


def _ensure_user(email: str, role: str) -> uuid.UUID:
    row = fetch_optional("SELECT user_id, role FROM users WHERE email = %s", (email,))
    if row is not None:
        display_name = DISPLAY_NAMES.get(
            email,
            email.split("@", maxsplit=1)[0].replace(".", " ").title(),
        )
        if row["role"] != role:
            execute(
                "UPDATE users SET role = %s WHERE user_id = %s", (role, row["user_id"])
            )
        execute(
            "UPDATE users SET full_name = %s WHERE user_id = %s",
            (display_name, row["user_id"]),
        )
        return row["user_id"]

    display_name = DISPLAY_NAMES.get(
        email,
        email.split("@", maxsplit=1)[0].replace(".", " ").title(),
    )
    created = execute_returning_one(
        """
        INSERT INTO users (user_id, email, password_hash, role, full_name)
        VALUES (%s, %s, %s, %s, %s)
        RETURNING user_id
        """,
        (uuid.uuid4(), email, hash_password(DEMO_PASSWORD), role, display_name),
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
    legacy_names: list[str] | None = None,
) -> None:
    if source_path.suffix.lower() == ".txt":
        text_content = source_path.read_text(encoding="utf-8")
    else:
        text_content = None

    candidate_names = list(dict.fromkeys([file_name, *(legacy_names or [])]))
    existing = fetch_optional(
        """
        SELECT file_id, status, name
          FROM documents
         WHERE case_id = %s
           AND name = ANY(%s::text[])
           AND is_latest = TRUE
         ORDER BY uploaded_at DESC
         LIMIT 1
        """,
        (case_id, candidate_names),
    )
    if existing is not None:
        renamed = False
        if existing["name"] != file_name:
            execute(
                "UPDATE documents SET name = %s WHERE file_id = %s",
                (file_name, existing["file_id"]),
            )
            renamed = True
        if existing["status"] == "ready" and not renamed:
            return
        temp_path = UPLOAD_TMP_DIR / f"{existing['file_id']}_{file_name}"
        UPLOAD_TMP_DIR.mkdir(parents=True, exist_ok=True)
        if text_content is not None:
            temp_path.write_text(text_content, encoding="utf-8")
        else:
            temp_path.write_bytes(source_path.read_bytes())
        ingest_document(
            file_path=temp_path,
            file_id=existing["file_id"],
            file_name=file_name,
            document_name=file_name,
            case_id=case_id,
            case_name=_case_name_for_id(case_id),
            assigned_lawyers=_assigned_lawyers_for_case(case_id),
            version=1,
        )
        return

    file_id = uuid.uuid4()
    execute_returning_one(
        """
        INSERT INTO documents (file_id, case_id, name, version, is_latest, status, uploaded_by)
        VALUES (%s, %s, %s, 1, TRUE, 'processing', %s)
        RETURNING file_id
        """,
        (file_id, case_id, file_name, uploaded_by),
    )

    temp_path = UPLOAD_TMP_DIR / f"{file_id}_{file_name}"
    UPLOAD_TMP_DIR.mkdir(parents=True, exist_ok=True)
    if text_content is not None:
        temp_path.write_text(text_content, encoding="utf-8")
    else:
        temp_path.write_bytes(source_path.read_bytes())

    ingest_document(
        file_path=temp_path,
        file_id=file_id,
        file_name=file_name,
        document_name=file_name,
        case_id=case_id,
        case_name=_case_name_for_id(case_id),
        assigned_lawyers=_assigned_lawyers_for_case(case_id),
        version=1,
    )


def _assigned_lawyers_for_case(case_id: uuid.UUID) -> list[uuid.UUID]:
    case_row = fetch_optional(
        "SELECT assigned_lawyers FROM cases WHERE case_id = %s",
        (case_id,),
    )
    return list(case_row["assigned_lawyers"] or []) if case_row else []


def _case_name_for_id(case_id: uuid.UUID) -> str | None:
    case_row = fetch_optional(
        "SELECT name FROM cases WHERE case_id = %s",
        (case_id,),
    )
    if case_row is None:
        return None
    return case_row["name"]


def _collect_demo_files() -> list[Path]:
    source_dir = ROOT_DEMO_DOCS_DIR if ROOT_DEMO_DOCS_DIR.exists() else DEMO_DOCS_DIR
    if not source_dir.exists():
        raise FileNotFoundError(
            f"Demo data directory not found. Expected either '{ROOT_DEMO_DOCS_DIR}' or '{DEMO_DOCS_DIR}'."
        )

    files = [
        path
        for path in sorted(source_dir.rglob("*"))
        if path.is_file() and path.suffix.lower() in ALLOWED_DEMO_SUFFIXES
    ]
    if not files:
        raise FileNotFoundError(
            f"No supported demo files found in '{source_dir}'. Add .pdf, .docx, .txt, or .eml files."
        )
    return files


def main() -> None:
    demo_files = _collect_demo_files()

    admin_id = _ensure_user(ADMIN_EMAIL, "admin")
    lawyer_id = _ensure_user(LAWYER_EMAIL, "lawyer")
    _ensure_user(LAWYER_TWO_EMAIL, "lawyer")
    _ensure_user(LAWYER_THREE_EMAIL, "lawyer")

    if ROOT_DEMO_DOCS_DIR.exists():
        case_name = "Finch Demo Matter"
        client_name = "Finch Legal Demo"
    else:
        case_name = "Core Demo Matter"
        client_name = "Atticus Demo"

    case_id = _ensure_case(
        name=case_name,
        client_name=client_name,
        created_by=admin_id,
        assigned_lawyer_id=lawyer_id,
    )

    for file_path in demo_files:
        display_name = _humanize_file_name(file_path.name)
        _ensure_document(
            case_id=case_id,
            uploaded_by=admin_id,
            file_name=display_name,
            source_path=file_path,
            legacy_names=[file_path.name],
        )


if __name__ == "__main__":
    main()
