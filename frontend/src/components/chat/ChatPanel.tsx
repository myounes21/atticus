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
      "Summarize recent filings from Sterling Corp",
      "Identify inconsistencies in deposition transcripts",
      "Draft a motion summary for the land transfer",
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
    <section className={variant === "lawyer-atelier" ? "flex min-h-0 flex-1 flex-col bg-surface" : "rounded-2xl border border-outline-variant/30 bg-white p-4 shadow-sm"}>
      {variant !== "lawyer-atelier" && (
        <div className="mb-4 flex items-center justify-between">
          <h2 className="font-headline text-lg font-bold text-on-surface">Case Assistant</h2>
          <span className="rounded-full bg-surface-container px-3 py-1 text-xs font-semibold text-on-surface-variant">
            {messages.length} turns
          </span>
        </div>
      )}

      {!caseId && <p className="text-sm text-on-surface-variant">Select a case to start chatting.</p>}
      {error && <p className="mb-3 text-sm text-red-600">{error}</p>}

      {caseId && messages.length === 0 && variant === "lawyer-atelier" && (
        <div className="flex flex-1 flex-col items-center justify-center px-6 pb-10">
          <div className="w-full max-w-2xl space-y-10 pt-8 text-center">
            <div className="space-y-4">
              <div className="signature-gradient mx-auto mb-8 flex h-16 w-16 items-center justify-center rounded-2xl text-white shadow-xl">
                <span className="material-symbols-outlined text-[32px]">bolt</span>
              </div>
              <h2 className="font-headline text-4xl font-extrabold tracking-tight text-on-surface">What&apos;s on the agenda today?</h2>
            </div>

            <div className="grid grid-cols-1 gap-4 text-left md:grid-cols-3">
              {suggestedPrompts.map((prompt, index) => (
                <button
                  key={prompt}
                  type="button"
                  className="group rounded-2xl border border-outline-variant/60 bg-white p-5 text-left transition-all duration-300 hover:-translate-y-0.5 hover:border-primary hover:bg-surface"
                  onClick={() => {
                    setQuery(prompt);
                    composerRef.current?.focus();
                    composerRef.current?.setSelectionRange(prompt.length, prompt.length);
                  }}
                  disabled={loading}
                >
                  <span className="material-symbols-outlined mb-3 block text-primary opacity-60 group-hover:opacity-100">
                    {index === 0 ? "description" : index === 1 ? "search_check" : "edit_note"}
                  </span>
                  <span className="block text-[13px] font-semibold leading-snug text-on-surface-variant">{prompt}</span>
                </button>
              ))}
            </div>
          </div>
        </div>
      )}

      {caseId && messages.length === 0 && variant !== "lawyer-atelier" && (
        <div className="mb-3 space-y-3">
          <p className="text-sm text-on-surface-variant">Start with one of these prompts, then continue naturally.</p>
          <div className="flex flex-wrap gap-2">
            {suggestedPrompts.map((prompt) => (
              <button
                key={prompt}
                type="button"
                className="rounded-full border border-outline-variant/40 bg-surface-container-low px-3 py-1.5 text-sm text-on-surface-variant hover:border-primary/40 hover:text-primary"
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

      {messages.length > 0 && (
        <div
          ref={threadRef}
          className={
            variant === "lawyer-atelier"
              ? "flex-1 overflow-y-auto px-6 pb-6 pt-6"
              : "mb-3 max-h-[520px] overflow-y-auto rounded-xl border border-outline-variant/30 bg-surface-container-lowest p-4"
          }
        >
          <div className={variant === "lawyer-atelier" ? "mx-auto w-full max-w-3xl space-y-5" : "space-y-4"}>
            {messages.map((message) => (
              <div key={message.id} className="space-y-3">
                <div className="ml-auto max-w-[88%] rounded-2xl bg-gradient-to-br from-primary to-primary-alt px-4 py-3 text-white shadow-sm">
                  <p className="mb-1 text-[10px] font-bold uppercase tracking-widest opacity-80">You</p>
                  <p className="whitespace-pre-wrap text-sm">{message.query}</p>
                </div>

                <div className="max-w-[88%] rounded-2xl border border-outline-variant/30 bg-white px-4 py-3 shadow-sm">
                  <p className="mb-1 text-[10px] font-bold uppercase tracking-widest text-on-surface-variant">Atticus</p>
                  <MarkdownText text={message.answer || (message.pending ? "" : "No response")} />

                  {message.pending && (
                    <div className="mt-3 inline-flex gap-1.5" aria-label="Assistant is typing">
                      <span className="h-2 w-2 animate-pulse rounded-full bg-outline" />
                      <span className="h-2 w-2 animate-pulse rounded-full bg-outline [animation-delay:120ms]" />
                      <span className="h-2 w-2 animate-pulse rounded-full bg-outline [animation-delay:240ms]" />
                    </div>
                  )}

                  {message.citations.length > 0 && (
                    <div className="mt-3 flex flex-wrap items-center gap-2">
                      <span className="text-[10px] font-bold uppercase tracking-widest text-outline">Sources</span>
                      {message.citations.map((item) => (
                        <span
                          key={`${message.id}-${item.chunk_id}`}
                          className="rounded-full border border-outline-variant/40 bg-surface-container-low px-2.5 py-1 text-xs text-on-surface-variant"
                        >
                          {item.document_name ?? item.chunk_id}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {caseId && (
        <div className={variant === "lawyer-atelier" ? "w-full px-6 pb-8" : "pt-1"}>
          <div className={variant === "lawyer-atelier" ? "mx-auto w-full max-w-3xl" : "w-full"}>
            <div className="rounded-3xl border border-outline-variant/60 bg-white p-2 shadow-2xl transition-all duration-500 focus-within:border-primary/40 focus-within:ring-4 focus-within:ring-primary/5">
              <textarea
                ref={composerRef}
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder={
                  variant === "lawyer-atelier"
                    ? "Ask anything about the Sterling Corp case..."
                    : "Message Atticus about this case..."
                }
                rows={1}
                className="h-20 w-full resize-none border-none bg-transparent p-4 text-[15px] font-medium placeholder:text-outline/40 focus:ring-0"
                onKeyDown={(event) => {
                  if (event.key === "Enter" && !event.shiftKey) {
                    event.preventDefault();
                    void submitQuestion();
                  }
                }}
              />

              <div className="flex items-center justify-between px-3 pb-2">
                {variant === "lawyer-atelier" ? (
                  <div className="flex items-center gap-1.5">
                    <button
                      type="button"
                      className="rounded-xl p-2 text-outline transition-all hover:bg-primary/5 hover:text-primary"
                      aria-label="Attach file"
                    >
                      <span className="material-symbols-outlined text-xl">attach_file</span>
                    </button>
                    <button
                      type="button"
                      className="rounded-xl p-2 text-outline transition-all hover:bg-primary/5 hover:text-primary"
                      aria-label="Voice input"
                    >
                      <span className="material-symbols-outlined text-xl">mic</span>
                    </button>
                    <button
                      type="button"
                      className="rounded-xl p-2 text-outline transition-all hover:bg-primary/5 hover:text-primary"
                      aria-label="Visual reference"
                    >
                      <span className="material-symbols-outlined text-xl">image</span>
                    </button>
                  </div>
                ) : (
                  <p className="text-xs text-on-surface-variant">Enter to send, Shift+Enter for new line</p>
                )}

                <button
                  type="button"
                  className={
                    variant === "lawyer-atelier"
                      ? "signature-gradient flex items-center gap-2.5 rounded-2xl px-6 py-2.5 text-white shadow-md transition-all hover:-translate-y-px hover:shadow-lg active:translate-y-px"
                      : "rounded-xl bg-primary px-4 py-2 text-sm font-semibold text-white disabled:opacity-60"
                  }
                  onClick={() => void submitQuestion()}
                  disabled={loading || !query.trim()}
                >
                  {variant === "lawyer-atelier" ? (
                    <>
                      <span className="text-[11px] font-extrabold uppercase tracking-widest">
                        {loading ? "Thinking..." : "Send"}
                      </span>
                      <span className="material-symbols-outlined text-lg">arrow_forward</span>
                    </>
                  ) : (
                    loading ? "Thinking..." : "Send"
                  )}
                </button>
              </div>
            </div>

            {variant === "lawyer-atelier" && (
              <div
                className="mt-8 flex items-center justify-center gap-6 text-[9px] font-bold uppercase tracking-[0.2em] text-outline opacity-70 md:gap-10"
                aria-label="Workspace compliance badges"
              >
                <div className="flex items-center gap-2">
                  <span className="material-symbols-outlined text-[14px]">verified_user</span>
                  <span>Privileged &amp; Confidential</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="material-symbols-outlined text-[14px]">memory</span>
                  <span>Atelier Legal v4.2</span>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </section>
  );
}
