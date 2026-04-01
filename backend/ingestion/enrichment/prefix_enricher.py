from backend.schemas.chunkers_schema import Chunk
from backend.ingestion.constants import STRUCTURE_MAP


def enrich_chunk(chunk: Chunk, case_name: str | None = None) -> Chunk:
    """Return a *new* Chunk with a contextual prefix prepended to its text."""
    prefix = _build_prefix(chunk, case_name)
    enriched_text = f"{prefix}\n{chunk.text}" if prefix else chunk.text
    return chunk.model_copy(update={"text": enriched_text})


def enrich_chunks(
    chunks: list[Chunk],
    case_name: str | None = None,
) -> list[Chunk]:
    """Enrich a batch of chunks (convenience wrapper)."""
    return [enrich_chunk(c, case_name) for c in chunks]


# ------------------------------------------------------------------
# Internal builders
# ------------------------------------------------------------------

def _build_prefix(chunk: Chunk, case_name: str | None) -> str:
    """Build the appropriate prefix based on the document's structure type."""
    structure = STRUCTURE_MAP.get(chunk.document_type, "unstructured")

    if structure == "conversational" and chunk.document_type == "email":
        return _email_prefix(chunk, case_name)
    elif structure == "conversational" and chunk.document_type == "deposition":
        return _deposition_prefix(chunk, case_name)
    elif structure == "sectioned":
        return _sectioned_prefix(chunk, case_name)
    elif structure == "narrative":
        return _narrative_prefix(chunk, case_name)
    else:
        return _unstructured_prefix(chunk, case_name)


def _email_prefix(chunk: Chunk, case_name: str | None) -> str:
    parts = ["Document Type: Email"]

    if case_name:
        parts.append(f"Case: {case_name}")
    if chunk.sender:
        parts.append(f"From: {chunk.sender}")
    if chunk.date:
        parts.append(f"Date: {chunk.date.strftime('%b %d %Y')}")
    if chunk.subject:
        parts.append(f"Subject: {chunk.subject}")

    return " | ".join(parts)


def _deposition_prefix(chunk: Chunk, case_name: str | None) -> str:
    parts = ["Document Type: Deposition"]

    if chunk.document_name:
        parts.append(f"Document: {chunk.document_name}")
    if case_name:
        parts.append(f"Case: {case_name}")

    return " | ".join(parts)


def _sectioned_prefix(chunk: Chunk, case_name: str | None) -> str:
    type_label = chunk.document_type.replace("_", " ").title()
    parts = [f"Document Type: {type_label}"]

    if chunk.document_name:
        parts.append(f"Document: {chunk.document_name}")
    if case_name:
        parts.append(f"Case: {case_name}")
    if chunk.section:
        parts.append(f"Section: {chunk.section}")

    return " | ".join(parts)


def _narrative_prefix(chunk: Chunk, case_name: str | None) -> str:
    type_label = chunk.document_type.replace("_", " ").title()
    parts = [f"Document Type: {type_label}"]

    if chunk.document_name:
        parts.append(f"Document: {chunk.document_name}")
    if case_name:
        parts.append(f"Case: {case_name}")
    if chunk.section:
        parts.append(f"Section: {chunk.section}")

    return " | ".join(parts)


def _unstructured_prefix(chunk: Chunk, case_name: str | None) -> str:
    type_label = chunk.document_type.replace("_", " ").title()
    parts = [f"Document Type: {type_label}"]

    if chunk.document_name:
        parts.append(f"Document: {chunk.document_name}")
    if case_name:
        parts.append(f"Case: {case_name}")

    return " | ".join(parts)
