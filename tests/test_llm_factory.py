"""Guards the two settings that were previously left to Ollama's defaults in
seven separate places: request timeout and temperature.

The last test is the architectural one — it fails if a future change starts
building an Ollama client somewhere other than llm.py, which is exactly how the
inconsistency arose the first time.
"""

from pathlib import Path

from multiagent_poc.config import settings
from multiagent_poc.llm import chat_model, embedding_model

SRC = Path(__file__).resolve().parents[1] / "src" / "multiagent_poc"


def test_chat_model_is_deterministic_by_default():
    """Answering a procedure and copying an order number into a form are
    extraction tasks; Ollama's ~0.8 default made them needlessly variable.
    """
    assert chat_model().temperature == settings.ollama_temperature
    assert settings.ollama_temperature == 0


def test_chat_model_temperature_can_be_overridden():
    assert chat_model(temperature=0.7).temperature == 0.7


def test_chat_model_has_a_bounded_timeout():
    """langchain-ollama has no timeout field of its own — it forwards
    client_kwargs to ollama.Client, so this asserts the plumbing, not just a
    stored value.
    """
    assert chat_model().client_kwargs["timeout"] == settings.ollama_timeout_seconds
    assert 0 < settings.ollama_timeout_seconds < 3600


def test_embedding_model_has_a_shorter_timeout_than_generation():
    assert embedding_model().client_kwargs["timeout"] == settings.ollama_embed_timeout_seconds
    assert settings.ollama_embed_timeout_seconds < settings.ollama_timeout_seconds


def test_ollama_clients_are_only_constructed_in_llm_module():
    offenders = []
    for path in SRC.rglob("*.py"):
        if path.name == "llm.py":
            continue
        text = path.read_text(encoding="utf-8")
        if "ChatOllama(" in text or "OllamaEmbeddings(" in text:
            offenders.append(str(path.relative_to(SRC)))

    assert not offenders, (
        "Ollama clients must be built via llm.chat_model()/embedding_model() so timeout "
        f"and temperature stay consistent; found direct construction in: {offenders}"
    )
