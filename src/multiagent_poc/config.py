"""Central config, loaded from environment (.env)."""

from dataclasses import dataclass
import os

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    ollama_base_url: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    ollama_model: str = os.getenv("OLLAMA_MODEL", "llama3.1:8b")
    chroma_persist_dir: str = os.getenv("CHROMA_PERSIST_DIR", "data/chroma")
    confidence_threshold: float = float(os.getenv("CONFIDENCE_THRESHOLD", "0.6"))
    langfuse_public_key: str | None = os.getenv("LANGFUSE_PUBLIC_KEY")
    langfuse_secret_key: str | None = os.getenv("LANGFUSE_SECRET_KEY")
    langfuse_host: str = os.getenv("LANGFUSE_HOST", "http://localhost:3000")


settings = Settings()
