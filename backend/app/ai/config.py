import os
from pathlib import Path


def _load_dotenv() -> None:
    # Load a simple .env file if present (no external dependency required).
    for candidate in (Path.cwd() / ".env", Path(__file__).resolve().parents[2] / ".env"):
        if candidate.is_file():
            try:
                for line in candidate.read_text().splitlines():
                    line = line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    key, value = line.split("=", 1)
                    os.environ.setdefault(key.strip(), value.strip())
            except OSError:
                pass


_load_dotenv()


def _default_nasa_cache_directory() -> str:
    # Vercel's filesystem is read-only outside /tmp, so on Vercel the cache
    # defaults to a writable temporary directory. Locally it stays ./cache/nasa.
    if os.getenv("VERCEL") or os.getenv("VERCEL_ENV"):
        return "/tmp/jamt-nasa-cache"
    return "./cache/nasa"


def get_config() -> dict:
    def _float(name: str, default: float) -> float:
        try:
            return float(os.getenv(name, str(default)))
        except ValueError:
            return default

    def _int(name: str, default: int) -> int:
        try:
            return int(os.getenv(name, str(default)))
        except ValueError:
            return default

    return {
        "llm_api_key": os.getenv("LLM_API_KEY") or os.getenv("OPENROUTER_API_KEY", ""),
        "llm_model": os.getenv("LLM_MODEL") or os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini"),
        "llm_base_url": os.getenv("LLM_BASE_URL") or os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
        "llm_timeout_seconds": _float("LLM_TIMEOUT_SECONDS", 45.0),
        "llm_max_tokens": _int("LLM_MAX_TOKENS", 800),
        "llm_temperature": _float("LLM_TEMPERATURE", 0.2),
        "openrouter_api_key": os.getenv("OPENROUTER_API_KEY", ""),
        "openrouter_model": os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini"),
        "openrouter_base_url": os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
        "backend_api_url": os.getenv("BACKEND_API_URL", "http://127.0.0.1:8000"),
        "chroma_persist_directory": os.getenv("CHROMA_PERSIST_DIRECTORY", "./chroma_db"),
        "embedding_model": os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2"),
        "tavily_api_key": os.getenv("TAVILY_API_KEY", ""),
        # Phase 2 — official NASA live data integration
        "nasa_data_enabled": os.getenv("NASA_DATA_ENABLED", "true").strip().lower() not in {"0", "false", "no"},
        "nasa_data_cache_ttl": _int("NASA_DATA_CACHE_TTL", 86400),
        "nasa_cache_directory": os.getenv("NASA_CACHE_DIRECTORY", _default_nasa_cache_directory()),
        "nasa_ntrs_base_url": os.getenv("NASA_NTRS_API_BASE_URL", "https://ntrs.nasa.gov/api"),
        "nasa_pds_base_url": os.getenv("NASA_PDS_API_BASE_URL", "https://pds.nasa.gov/api/search/1"),
        "nasa_api_key": os.getenv("NASA_API_KEY", ""),
    }
