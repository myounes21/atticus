import uuid

from backend.generation import chat_history


def test_get_history_hydrates_from_db(monkeypatch) -> None:
    conversation_id = uuid.uuid4()
    chat_history.clear_history(conversation_id)

    monkeypatch.setattr(
        "backend.generation.chat_history.fetch_all",
        lambda query, params: [
            {"query": "new question", "answer": "new answer"},
            {"query": "old question", "answer": "old answer"},
        ],
    )

    history = chat_history.get_history(conversation_id, n=2)

    assert history == [
        {"role": "user", "content": "old question"},
        {"role": "assistant", "content": "old answer"},
        {"role": "user", "content": "new question"},
        {"role": "assistant", "content": "new answer"},
    ]


def test_get_history_uses_memory_after_hydration(monkeypatch) -> None:
    conversation_id = uuid.uuid4()
    chat_history.clear_history(conversation_id)
    calls = {"count": 0}

    def _fake_fetch_all(query, params):
        calls["count"] += 1
        return [{"query": "q1", "answer": "a1"}]

    monkeypatch.setattr("backend.generation.chat_history.fetch_all", _fake_fetch_all)

    first = chat_history.get_history(conversation_id)
    second = chat_history.get_history(conversation_id)

    assert first == second
    assert calls["count"] == 1

