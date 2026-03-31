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

export default function ChatPanel({
  caseId,
  variant = "default",
}: {
  caseId: string | null;
  variant?: "default" | "lawyer-atelier";
}) {
  const [query, setQuery] = useState("");
  const [conversationId, setConversationId] = useState<string | undefined>();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const threadRef = useRef<HTMLDivElement | null>(null);
  const composerRef = useRef<HTMLTextAreaElement | null>(null);

  const suggestedPrompts = useMemo(
    () => [
      "Give me a 6-bullet case brief: parties, accusation, evidence gaps, and likely verdict risk.",
      "From Defense Brief V1.docx and Medical Report.pdf, summarize the physical impossibility argument.",
      "Compare Mayella Ewell Deposition.txt and Tom Robinson Deposition.txt for contradictions.",
      "Use Contradictions Log.txt and Incident Timeline.txt to propose cross-examination questions.",
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
    <section className={variant === "lawyer-atelier" ? "lawyer-chat-scene" : "card chat-shell modern-chat-shell"}>
      {variant !== "lawyer-atelier" && (
        <div className="section-head">
          <h2>Case Assistant</h2>
          <span className="pill subtle">{messages.length} turns</span>
        </div>
      )}
      {!caseId && <p className="muted">Select a case to start chatting.</p>}
      {error && <p className="error-text">{error}</p>}

      {caseId && messages.length === 0 && (
        <div className={variant === "lawyer-atelier" ? "lawyer-empty-showcase" : "chat-empty"}>
          {variant === "lawyer-atelier" ? (
            <>
              <div className="lawyer-empty-icon">
                <span className="material-symbols-outlined">bolt</span>
              </div>
              <h2>What&apos;s on the agenda today?</h2>
              <div className="lawyer-prompt-grid">
                {suggestedPrompts.slice(0, 3).map((prompt, index) => (
                  <button
                    key={prompt}
                    type="button"
                    className="lawyer-prompt-card"
                    onClick={() => {
                      setQuery(prompt);
                      composerRef.current?.focus();
                      composerRef.current?.setSelectionRange(prompt.length, prompt.length);
                    }}
                    disabled={loading}
                  >
                    <span className="material-symbols-outlined">
                      {index === 0 ? "description" : index === 1 ? "search_check" : "edit_note"}
                    </span>
                    <span>{prompt}</span>
                  </button>
                ))}
              </div>
            </>
          ) : (
            <>
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
            </>
          )}
        </div>
      )}

      {(variant !== "lawyer-atelier" || messages.length > 0) && (
        <div
          ref={threadRef}
          className={variant === "lawyer-atelier" ? "chat-thread modern-thread lawyer-thread" : "chat-thread modern-thread"}
        >
          {messages.length === 0 && caseId && variant !== "lawyer-atelier" && (
            <p className="muted">No messages yet. Send your first message.</p>
          )}
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
      )}

      <div className={variant === "lawyer-atelier" ? "chat-composer lawyer-floating-composer" : "chat-composer modern-composer"}>
        <textarea
          ref={composerRef}
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder={variant === "lawyer-atelier" ? "Ask anything about the active case..." : "Message Atticus about this case..."}
          rows={1}
          onKeyDown={(event) => {
            if (event.key === "Enter" && !event.shiftKey) {
              event.preventDefault();
              void submitQuestion();
            }
          }}
        />
        <div className="row composer-actions">
          {variant === "lawyer-atelier" ? (
            <div className="lawyer-composer-tools">
              <button type="button" className="lawyer-tool-btn" aria-label="Attach file">
                <span className="material-symbols-outlined">attach_file</span>
              </button>
              <button type="button" className="lawyer-tool-btn" aria-label="Voice input">
                <span className="material-symbols-outlined">mic</span>
              </button>
              <button type="button" className="lawyer-tool-btn" aria-label="Visual reference">
                <span className="material-symbols-outlined">image</span>
              </button>
            </div>
          ) : (
            <p className="muted composer-tip">Enter to send, Shift+Enter for new line</p>
          )}
          <button
            type="button"
            className={variant === "lawyer-atelier" ? "send-btn lawyer-send-btn signature-gradient" : "send-btn"}
            onClick={() => void submitQuestion()}
            disabled={loading || !caseId || !query.trim()}
          >
            {loading ? "Thinking..." : "Send"}
            {variant === "lawyer-atelier" ? <span className="material-symbols-outlined">arrow_forward</span> : null}
          </button>
        </div>
      </div>
    </section>
  );
}
