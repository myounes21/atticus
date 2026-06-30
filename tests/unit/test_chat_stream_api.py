import json
import uuid

from fastapi.testclient import TestClient

from backend.api.main import app
from backend.core.dependencies import CurrentUser, get_current_user


def _set_lawyer_override(user_id: uuid.UUID) -> None:
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        user_id=user_id,
        role="lawyer",
    )


def _clear_overrides() -> None:
    app.dependency_overrides.clear()


def _extract_events(response_text: str) -> list[dict]:
    events: list[dict] = []
    for block in response_text.strip().split("\n\n"):
        if not block.strip():
            continue
        data_lines = [line[5:].strip() for line in block.split("\n") if line.startswith("data:")]
        if not data_lines:
            continue
        events.append(json.loads("\n".join(data_lines)))
    return events


def test_chat_stream_emits_tokens_and_done(monkeypatch) -> None:
    user_id = uuid.uuid4()
    case_id = uuid.uuid4()

    monkeypatch.setattr("backend.api.routes.chat.enforce_rate_limit", lambda **kwargs: None)
    monkeypatch.setattr(
        "backend.api.routes.chat.fetch_optional",
        lambda query, params: {"assigned_lawyers": [user_id]},
    )
    monkeypatch.setattr("backend.api.routes.chat.get_history", lambda conversation_id: [])
    monkeypatch.setattr("backend.api.routes.chat.is_general_query", lambda query: True)
    monkeypatch.setattr(
        "backend.api.routes.chat.build_general_messages",
        lambda query, chat_history: [{"role": "user", "content": query}],
    )
    monkeypatch.setattr(
        "backend.api.routes.chat.generate_stream",
        lambda messages: iter(["Hello ", "stream!"]),
    )
    monkeypatch.setattr("backend.api.routes.chat.append_turn", lambda *args, **kwargs: None)
    monkeypatch.setattr("backend.api.routes.chat.execute", lambda *args, **kwargs: None)

    _set_lawyer_override(user_id)
    try:
        client = TestClient(app)
        response = client.post(
            "/chat/stream",
            json={"query": "hello", "case_id": str(case_id)},
        )
    finally:
        _clear_overrides()

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")

    events = _extract_events(response.text)
    assert len(events) >= 3
    assert events[0]["type"] == "token"
    assert events[0]["content"] == "Hello "
    assert events[1]["type"] == "token"
    assert events[1]["content"] == "stream!"

    done = events[-1]
    assert done["type"] == "done"
    assert uuid.UUID(done["content"]["conversation_id"])
    assert uuid.UUID(done["content"]["message_id"])


def test_chat_stream_emits_error_event_on_generator_failure(monkeypatch) -> None:
    user_id = uuid.uuid4()
    case_id = uuid.uuid4()

    monkeypatch.setattr("backend.api.routes.chat.enforce_rate_limit", lambda **kwargs: None)
    monkeypatch.setattr(
        "backend.api.routes.chat.fetch_optional",
        lambda query, params: {"assigned_lawyers": [user_id]},
    )
    monkeypatch.setattr("backend.api.routes.chat.get_history", lambda conversation_id: [])
    monkeypatch.setattr("backend.api.routes.chat.is_general_query", lambda query: True)
    monkeypatch.setattr(
        "backend.api.routes.chat.build_general_messages",
        lambda query, chat_history: [{"role": "user", "content": query}],
    )

    def _broken_stream(messages):
        raise RuntimeError("llm unavailable")

    monkeypatch.setattr("backend.api.routes.chat.generate_stream", _broken_stream)

    _set_lawyer_override(user_id)
    try:
        client = TestClient(app)
        response = client.post(
            "/chat/stream",
            json={"query": "hello", "case_id": str(case_id)},
        )
    finally:
        _clear_overrides()

    assert response.status_code == 200

    events = _extract_events(response.text)
    assert len(events) == 1
    assert events[0]["type"] == "error"
    assert "llm unavailable" in events[0]["content"]

