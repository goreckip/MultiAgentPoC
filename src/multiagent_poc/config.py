"""Central config, loaded from environment (.env)."""

from dataclasses import dataclass
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Settings:
    ollama_base_url: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    ollama_model: str = os.getenv("OLLAMA_MODEL", "llama3.1:8b")
    ollama_embed_model: str = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")
    # Deterministic by default: answering a procedure and filling document fields
    # are extraction tasks, not creative ones. Ollama's own default is ~0.8, which
    # is where a chunk of the observed run-to-run variance came from.
    ollama_temperature: float = float(os.getenv("OLLAMA_TEMPERATURE", "0"))
    # Generous but finite. A generation on CPU has been measured at ~215s, so the
    # ceiling is set well above that — the point is to fail eventually rather than
    # hang a request (and a Streamlit spinner) forever on an unresponsive Ollama.
    ollama_timeout_seconds: float = float(os.getenv("OLLAMA_TIMEOUT_SECONDS", "600"))
    # Embeddings are ~3s in practice; no reason to wait minutes for one.
    ollama_embed_timeout_seconds: float = float(os.getenv("OLLAMA_EMBED_TIMEOUT_SECONDS", "120"))
    chroma_persist_dir: str = os.getenv("CHROMA_PERSIST_DIR", str(PROJECT_ROOT / "data/chroma"))
    confidence_threshold: float = float(os.getenv("CONFIDENCE_THRESHOLD", "0.6"))
    langfuse_public_key: str | None = os.getenv("LANGFUSE_PUBLIC_KEY")
    langfuse_secret_key: str | None = os.getenv("LANGFUSE_SECRET_KEY")
    # Langfuse Cloud free tier — regional hosts: https://us.cloud.langfuse.com or
    # https://cloud.langfuse.com (EU). No self-hosted Docker instance for this project.
    langfuse_host: str = os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")
    # Local ClamAV install (portable, not installed system-wide — see decision_log.md).
    # Path to the clamscan.exe binary and the folder holding main.cvd/daily.cvd/bytecode.cvd.
    clamscan_path: str = os.getenv(
        "CLAMSCAN_PATH", str(PROJECT_ROOT / ".clamav/clamav-1.5.4.win.x64/clamscan.exe")
    )
    clamav_db_path: str = os.getenv(
        "CLAMAV_DB_PATH", str(PROJECT_ROOT / ".clamav/clamav-1.5.4.win.x64/db")
    )
    max_attachment_size_bytes: int = int(os.getenv("MAX_ATTACHMENT_SIZE_BYTES", str(10 * 1024 * 1024)))  # 10 MB


settings = Settings()
