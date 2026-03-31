"""Prompt builder — constructs the legal-aware system + context prompt.

Rules encoded in the system prompt:
  • Answer ONLY from the provided context.
  • Cite every claim: [Source: {doc_name}, v{version}, p{page}].
  • If the answer is not found: say "I don't have that information."
"""

from __future__ import annotations

from backend.retrieval.reranker import RerankedChunk

_SYSTEM_PROMPT = """\
You are Atticus, a legal research assistant for a law firm. You answer questions \
based ONLY on the provided document context. Follow these rules strictly:

1. Answer ONLY from the context below. Do NOT use external knowledge.
2. Cite every factual claim with the format: [Source: {document_name}, p{page}]
3. If the context does not contain enough information to answer, respond with: \
"I don't have enough information in the available documents to answer this question."
4. Be precise with legal terminology.
5. If multiple documents support the same point, cite all of them.
6. Output valid markdown only.
7. Keep answers concise and scannable:
   - Start with one direct sentence that answers the question.
   - Then use short bullet points for supporting details.
   - For labeled fields (for example Parties, Claims, Relief), format each as:
     - **Label:** value [Source: ...]
   - Avoid dense paragraphs, run-on lists, or inline "* item * item" formatting.
8. Do not say phrases like "Based on the provided context" or "According to context documents".
9. For unknown pages, use p? in the citation.
10. For list-style answers, use `- ` bullets only, one item per line.
11. Never cite context labels (for example "Context 1"). Citations must use the exact document file name.
12. If the same document appears multiple times in context, list it once unless the user asks for duplicates.
"""


def build_prompt(
    query: str,
    chunks: list[RerankedChunk],
    chat_history: list[dict[str, str]] | None = None,
) -> list[dict[str, str]]:
    """Build the full message list for the LLM.

    Returns:
        List of messages in OpenAI-compatible format:
        ``[{"role": "system"|"user"|"assistant", "content": "..."}]``
    """
    messages: list[dict[str, str]] = [
        {"role": "system", "content": _SYSTEM_PROMPT},
    ]

    # Append chat history for multi-turn context
    if chat_history:
        for msg in chat_history[-10:]:  # last 5 turns max
            messages.append(msg)

    # Build context block from retrieved chunks
    context_parts: list[str] = []
    for i, chunk in enumerate(chunks, start=1):
        doc_name = chunk.payload.get("document_name", "Unknown Document")
        doc_type = chunk.payload.get("document_type", "document")
        chunk_index = chunk.payload.get("chunk_index", "?")

        header = f"[Document {i}] Name: {doc_name} | Type: {doc_type.title()}"
        context_parts.append(f"{header}\n{chunk.text}")

    context_block = (
        "\n\n---\n\n".join(context_parts)
        if context_parts
        else "(No relevant context found)"
    )

    user_message = f"## Context Documents\n\n{context_block}\n\n## Question\n\n{query}"

    messages.append({"role": "user", "content": user_message})
    return messages
