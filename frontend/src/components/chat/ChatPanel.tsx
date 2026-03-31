"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { askChat, askChatStream, type ChatCitation } from "@/lib/api";
import MarkdownText from "@/components/chat/MarkdownText";

type ChatMessage = {
  id: string;
  query: string;
  answer: string;
  citations: ChatCitation[];
  pending?: boolean;
};

export default function ChatPanel({ caseId }: { caseId: string | null }) {
  const [query, setQuery] = useState("");
  const [conversationId, setConversationId] = useState<string | undefined>();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const threadRef = useRef<HTMLDivElement | null>(null);
  const composerRef = useRef<HTMLTextAreaElement | null>(null);

  const suggestedPrompts = useMemo(
    () => [
      "Give me a 6-bullet case brief: parties, claims, and requested relief.",
      "From Evidence Bundle Demo.pdf, what attribution facts are strongest for court?",
      "From Legal Email Threads Demo.eml, who escalated urgency and what NDA clause was cited?",
      "From Acme NDA Northstar Counsel.txt, what are the highest-risk obligations for Northstar?",
    ],
    [],
  );

  useEffect(() => {
    setConversationId(undefined);
    setMessages([]);
    setError("");
    setQuery("");
  }, [caseId]);

  useEffect(() => {
    if (!threadRef.current) {
      return;
    }
    threadRef.current.scrollTop = threadRef.current.scrollHeight;
  }, [messages, loading]);

  useEffect(() => {
    if (!composerRef.current) {
      return;
    }
    composerRef.current.style.height = "auto";
    const nextHeight = Math.min(composerRef.current.scrollHeight, 220);
    composerRef.current.style.height = `${Math.max(nextHeight, 44)}px`;
  }, [query]);

  async function submitQuestion() {
    if (!caseId || !query.trim()) return;
    const outgoing = query.trim();
    const pendingId = `pending-${Date.now()}`;

    setMessages((prev) => [
      ...prev,
      {
        id: pendingId,
        query: outgoing,
        answer: "",
        citations: [],
        pending: true,
      },
    ]);
    setQuery("");
    setLoading(true);
    setError("");

    try {
      const response = await askChatStream(
        {
          query: outgoing,
          case_id: caseId,
          conversation_id: conversationId,
        },
        {
          onToken: (_token, fullText) => {
            setMessages((prev) =>
              prev.map((item) =>
                item.id === pendingId
                  ? {
                      ...item,
                      answer: fullText,
                    }
                  : item,
              ),
            );
          },
          onCitation: (citation) => {
            setMessages((prev) =>
              prev.map((item) =>
                item.id === pendingId
                  ? {
                      ...item,
                      citations: item.citations.some((entry) => entry.chunk_id === citation.chunk_id)
                        ? item.citations
                        : [...item.citations, citation],
                    }
                  : item,
              ),
            );
          },
        },
      ).catch(async () => {
        return askChat({
          query: outgoing,
          case_id: caseId,
          conversation_id: conversationId,
        });
      });

      setConversationId(response.conversation_id);
      setMessages((prev) =>
        prev.map((item) =>
          item.id === pendingId
            ? {
                id: response.message_id,
                query: outgoing,
                answer: response.answer,
                citations: response.chunks_used,
                pending: false,
              }
            : item,
        ),
      );
    } catch (err) {
      setMessages((prev) => prev.filter((item) => item.id !== pendingId));
      setError(err instanceof Error ? err.message : "Chat request failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="card chat-shell modern-chat-shell">
      <div className="section-head">
        <h2>Case Assistant</h2>
        <span className="pill subtle">{messages.length} turns</span>
      </div>
      {!caseId && <p className="muted">Select a case to start chatting.</p>}
      {error && <p className="error-text">{error}</p>}

      {caseId && messages.length === 0 && (
        <div className="chat-empty">
          <p className="muted">Start with one of these prompts, then continue naturally.</p>
          <div className="prompt-chip-row">
            {suggestedPrompts.map((prompt) => (
            <button
              key={prompt}
              type="button"
              className="secondary prompt-chip"
              onClick={() => {
                setQuery(prompt);
                composerRef.current?.focus();
                composerRef.current?.setSelectionRange(prompt.length, prompt.length);
              }}
              disabled={loading}
            >
                {prompt}
              </button>
            ))}
          </div>
        </div>
      )}

      <div ref={threadRef} className="chat-thread modern-thread">
        {messages.length === 0 && caseId && <p className="muted">No messages yet. Send your first message.</p>}
        {messages.map((message) => (
          <div key={message.id} className="chat-turn">
            <div className="chat-bubble user glass-bubble">
              <p className="chat-meta">You</p>
              <p className="chat-user-text">{message.query}</p>
            </div>

            <div className="chat-bubble assistant elevated-bubble">
              <p className="chat-meta">Atticus</p>
              <MarkdownText text={message.answer || (message.pending ? "" : "No response")} />
              {message.pending && (
                <div className="typing-indicator" aria-label="Assistant is typing">
                  <span />
                  <span />
                  <span />
                </div>
              )}
              {message.citations.length > 0 && (
                <div className="source-tags">
                  <span className="source-label">Sources</span>
                  {message.citations.map((item) => (
                    <span key={`${message.id}-${item.chunk_id}`} className="source-tag">
                      {item.document_name ?? item.chunk_id}
                    </span>
                  ))}
                </div>
              )}
            </div>
          </div>
        ))}
      </div>

      <div className="chat-composer modern-composer">
        <textarea
          ref={composerRef}
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Message Atticus about this case..."
          rows={1}
          onKeyDown={(event) => {
            if (event.key === "Enter" && !event.shiftKey) {
              event.preventDefault();
              void submitQuestion();
            }
          }}
        />
        <div className="row composer-actions">
          <p className="muted composer-tip">Enter to send, Shift+Enter for new line</p>
          <button
            type="button"
            className="send-btn"
            onClick={() => void submitQuestion()}
            disabled={loading || !caseId || !query.trim()}
          >
            {loading ? "Thinking..." : "Send"}
          </button>
        </div>
      </div>
    </section>
  );
}
