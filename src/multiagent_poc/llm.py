"""The only place Ollama clients are constructed.

Before this module the seven call sites each built their own client, which meant
every one of them silently inherited Ollama's defaults: no request timeout (an
unresponsive server hung the request, and the Streamlit spinner, forever) and
temperature ~0.8 on tasks — quoting a procedure, copying an order number into a
form — where creativity is a defect rather than a feature.

Centralising construction means those two settings are decided once. Callers
that genuinely need something different pass it explicitly; the LLM-as-judge is
the only current example, and it wants the same determinism anyway.
"""

from langchain_ollama import ChatOllama, OllamaEmbeddings

from multiagent_poc.config import settings


def chat_model(temperature: float | None = None) -> ChatOllama:
    """Chat client with a bounded request timeout.

    langchain-ollama exposes no `timeout` field of its own — it forwards
    `client_kwargs` to `ollama.Client`, which hands them to httpx. That
    indirection is the reason this lives in one place instead of seven.
    """
    return ChatOllama(
        model=settings.ollama_model,
        base_url=settings.ollama_base_url,
        temperature=settings.ollama_temperature if temperature is None else temperature,
        client_kwargs={"timeout": settings.ollama_timeout_seconds},
    )


def embedding_model() -> OllamaEmbeddings:
    """Embedding client with a shorter timeout than generation — embeddings take
    seconds, so waiting minutes for one only ever means something is wrong.
    """
    return OllamaEmbeddings(
        model=settings.ollama_embed_model,
        base_url=settings.ollama_base_url,
        client_kwargs={"timeout": settings.ollama_embed_timeout_seconds},
    )
