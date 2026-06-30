import logging
from typing import Iterator

from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from ollama import Client

from config import settings

logger = logging.getLogger(__name__)


def _get_client() -> Client:
    return Client(host=settings.ollama_base_url)


def generate(
    messages: list[dict[str, str]],
    model: str | None = None,
    temperature: float = 0.1,
    max_tokens: int = 2048,
) -> str:
    """Synchronous LLM call.  Returns the full answer as a string."""
    groq_gen = ChatGroq(model_name="llama-3.1-8b-instant", temperature=temperature, max_tokens=max_tokens)
    
    lc_messages = []
    for m in messages:
        if m["role"] == "system":
            lc_messages.append(SystemMessage(content=m["content"]))
        elif m["role"] == "user":
            lc_messages.append(HumanMessage(content=m["content"]))
        else:
            lc_messages.append(AIMessage(content=m["content"]))
            
    response = groq_gen.invoke(lc_messages)
    return response.content


def generate_stream(
    messages: list[dict[str, str]],
    model: str | None = None,
    temperature: float = 0.1,
    max_tokens: int = 2048,
) -> Iterator[str]:
    """Streaming LLM call.  Yields tokens one at a time."""
    client = _get_client()
    model = model or settings.ollama_model

    stream = client.chat(
        model=model,
        messages=messages,
        options={"temperature": temperature, "num_predict": max_tokens},
        stream=True,
    )

    for chunk in stream:
        content = chunk.get("message", {}).get("content")
        if content:
            yield content
