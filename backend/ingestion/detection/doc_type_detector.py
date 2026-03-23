from groq import Groq
from config import settings
from groq.types.chat import ChatCompletionUserMessageParam


client = Groq(api_key=settings.groq_api_key)


_CATEGORIES = {
    "email",
    "contract",
    "brief",
    "note",
    "invoice",
    "deposition",
    "court_filing",
    "settlement",
    "legal_notice",
    "evidence",
}

_ALIASES = {
    "legal_brief": "brief",
    "court filing": "court_filing",
    "court-filing": "court_filing",
    "legal notice": "legal_notice",
    "legal-notice": "legal_notice",
}

_MAX_ITERATION = 2

_PROMPT = """
You are a legal document classifier.

Classify the document into exactly one category from this list:
- email
- contract
- brief
- note
- invoice
- deposition
- court_filing
- settlement
- legal_notice
- evidence

Document:
{content}

Return exactly one category name from the list above. Nothing else.
"""

def _get_llm_response(content:str) -> str:
    response = client.chat.completions.create(
        model=settings.groq_llm_model,
        messages=[
            ChatCompletionUserMessageParam(role="user", content=_PROMPT.format(content=content))
        ]
    )
    result = response.choices[0].message.content
    result = result.lower().strip().replace(" ", "_")

    # not in categories, but maybe it's a known alias
    if result not in _CATEGORIES:
        result = _ALIASES.get(result, result)

    return result

def detect(content: str, file_type: str) -> str:
    if file_type == "eml":
        return "email"

    if file_type == "txt":
        return "note"

    for _ in range(_MAX_ITERATION):
        llm_result = _get_llm_response(content)
        if llm_result in _CATEGORIES:
            return llm_result

    raise ValueError(f"Could not classify document: LLM returned '{llm_result}'")
