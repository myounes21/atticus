"use client";

import { useEffect, useState } from "react";
import { askChat, type ChatCitation } from "@/lib/api";

type ChatMessage = {
  id: string;
  query: string;
  answer: string;
  citations: ChatCitation[];
};

export default function ChatPanel({ caseId }: { caseId: string | null }) {
  const [query, setQuery] = useState("");
  const [conversationId, setConversationId] = useState<string | undefined>();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    setConversationId(undefined);
    setMessages([]);
    setError("");
    setQuery("");
  }, [caseId]);

  async function submitQuestion() {
    if (!caseId || !query.trim()) return;
    setLoading(true);
    setError("");
    try {
      const response = await askChat({
        query: query.trim(),
        case_id: caseId,
        conversation_id: conversationId,
      });
      setConversationId(response.conversation_id);
      setMessages((prev) => [
        ...prev,
        {
          id: response.message_id,
          query: query.trim(),
          answer: response.answer,
          citations: response.chunks_used,
        },
      ]);
      setQuery("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Chat request failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="card">
      <div className="section-head">
        <h2>Case Chat</h2>
        <span className="pill subtle">{messages.length} turns</span>
      </div>
      {!caseId && <p className="muted">Select a case to start chatting.</p>}
      {error && <p className="error-text">{error}</p>}

      <div className="stack-sm">
        {messages.length === 0 && caseId && <p className="muted">No messages yet. Ask your first question.</p>}
        {messages.map((message) => (
          <div key={message.id} className="chat-item">
            <p>
              <strong>Q:</strong> {message.query}
            </p>
            <p>
              <strong>A:</strong> {message.answer}
            </p>
            {message.citations.length > 0 && (
              <p className="muted citations">
                Sources: {message.citations.map((item) => item.document_name ?? item.chunk_id).join(", ")}
              </p>
            )}
          </div>
        ))}
      </div>

      <div className="row chat-input-row">
        <textarea
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Ask a question about this case..."
          rows={3}
          onKeyDown={(event) => {
            if ((event.metaKey || event.ctrlKey) && event.key === "Enter") {
              event.preventDefault();
              void submitQuestion();
            }
          }}
        />
        <button
          type="button"
          onClick={() => void submitQuestion()}
          disabled={loading || !caseId || !query.trim()}
        >
          {loading ? "Asking..." : "Ask"}
        </button>
      </div>
      <p className="muted">Tip: press Ctrl/Cmd + Enter to submit quickly.</p>
    </section>
  );
}
