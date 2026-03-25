from backend.ingestion.detection import doc_type_detector


def test_detect_normalizes_noncompliant_llm_output(monkeypatch) -> None:
    monkeypatch.setattr(
        doc_type_detector,
        "_classify_with_groq",
        lambda content: doc_type_detector._normalize_detector_output(
            "This document appears to be a contract."
        ),
    )

    detected = doc_type_detector.detect("Some agreement text")

    assert detected.category == "unknown"
    assert detected.structure_type == "unstructured"
    assert detected.needs_review is True


def test_detect_maps_legacy_alias(monkeypatch) -> None:
    monkeypatch.setattr(
        doc_type_detector,
        "_classify_with_groq",
        lambda content: doc_type_detector._normalize_detector_output("legal_brief"),
    )

    detected = doc_type_detector.detect("Legal argument")

    assert detected.category == "brief"
    assert detected.structure_type == "narrative"
    assert detected.needs_review is False


def test_detect_uses_llm_result_directly(monkeypatch) -> None:
    monkeypatch.setattr(
        doc_type_detector,
        "_classify_with_groq",
        lambda content: "contract",
    )

    detected = doc_type_detector.detect("Hi team")

    assert detected.category == "contract"
    assert detected.structure_type == "sectioned"
    assert detected.needs_review is False


def test_detect_marks_unknown_when_no_signal(monkeypatch) -> None:
    monkeypatch.setattr(doc_type_detector, "_classify_with_groq", lambda content: None)

    detected = doc_type_detector.detect("Random text without legal markers")

    assert detected.category == "unknown"
    assert detected.structure_type == "unstructured"
    assert detected.needs_review is True


def test_detect_txt_shortcut_keeps_note_for_short_content() -> None:
    detected = doc_type_detector.detect("tiny note", "txt")

    assert detected.category == "note"
    assert detected.structure_type == "unstructured"
    assert detected.needs_review is False


def test_detect_txt_long_content_uses_classifier(monkeypatch) -> None:
    monkeypatch.setattr(doc_type_detector, "_classify_with_groq", lambda content: "deposition")

    detected = doc_type_detector.detect("x" * 1000, "txt")

    assert detected.category == "deposition"
    assert detected.structure_type == "conversational"
    assert detected.needs_review is False


