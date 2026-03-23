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

    assert detected == "contract"


def test_detect_maps_legacy_alias(monkeypatch) -> None:
    monkeypatch.setattr(
        doc_type_detector,
        "_classify_with_groq",
        lambda content: doc_type_detector._normalize_detector_output("legal_brief"),
    )

    detected = doc_type_detector.detect("Legal argument")

    assert detected == "brief"


def test_detect_uses_llm_result_directly(monkeypatch) -> None:
    monkeypatch.setattr(
        doc_type_detector,
        "_classify_with_groq",
        lambda content: "contract",
    )

    detected = doc_type_detector.detect("Hi team")

    assert detected == "contract"


def test_detect_defaults_to_note_when_no_signal(monkeypatch) -> None:
    monkeypatch.setattr(doc_type_detector, "_classify_with_groq", lambda content: None)

    detected = doc_type_detector.detect("Random text without legal markers")

    assert detected == "note"


