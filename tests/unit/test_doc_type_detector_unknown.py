from backend.ingestion.detection import doc_type_detector


def test_normalize_llm_result_returns_unknown_for_garbage() -> None:
    assert doc_type_detector._normalize_llm_result("asdasd ???") == "unknown"


def test_detect_marks_unknown_as_needing_review(monkeypatch) -> None:
    monkeypatch.setattr(
        doc_type_detector,
        "_get_llm_response",
        lambda content: doc_type_detector._LLMOutcome(
            raw_label="???",
            normalized_label="unknown",
            attempts=1,
            error=None,
        ),
    )

    detected = doc_type_detector.detect("garbage content", "pdf")

    assert detected.category == "unknown"
    assert detected.structure_type == "unstructured"
    assert detected.needs_review is True
    assert detected.normalized_label == "unknown"

