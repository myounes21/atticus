import logging

from groq import Groq

from config import settings

logger = logging.getLogger(__name__)

_REWRITE_SYSTEM_PROMPT = """\
You are a legal search query optimizer. Your job is to rewrite the user's
query into a more detailed search query that will retrieve the most relevant
legal documents. Keep the legal terminology precise. Do NOT answer the
question — only rewrite it.

Rules:
- Output only the rewritten query, nothing else.
- Preserve case references, party names, and dates.
- Expand abbreviations and add synonyms where helpful.
- If the query is already detailed enough, return it unchanged.
"""


def rewrite(
    query: str,
    chat_history: list[dict[str, str]] | None = None,
) -> str:
    """Rewrite *query* into a richer search query.

    *chat_history* (optional) is a list of ``{"role": ..., "content": ...}``
    messages for multi-turn context.
    """
    if not query.strip():
        return query

    # Keep specific user queries unchanged to avoid losing key constraints.
    token_count = len(query.split())
    has_digits = any(char.isdigit() for char in query)
    if token_count >= 9 or has_digits:
        return query

    messages: list[dict[str, str]] = [
        {"role": "system", "content": _REWRITE_SYSTEM_PROMPT},
    ]

    # Include recent history for context
    if chat_history:
        for msg in chat_history[-4:]:  # last 2 turns
            messages.append(msg)

    messages.append({"role": "user", "content": query})

    try:
        client = Groq(api_key=settings.groq_api_key)
        response = client.chat.completions.create(
            model=settings.groq_llm_model,
            messages=messages,
            temperature=0.0,
            max_tokens=256,
        )
        rewritten = response.choices[0].message.content.strip()
        if rewritten:
            logger.info("Rewrote query: '%s' → '%s'", query, rewritten)
            return rewritten
    except Exception:
        logger.warning("Query rewrite failed, using original query", exc_info=True)

    return query
