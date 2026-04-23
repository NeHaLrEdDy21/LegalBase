"""
Application configuration — loaded from environment variables / .env file.
All settings are validated by Pydantic at startup.
"""
from functools import lru_cache
from pathlib import Path
from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _find_env_file() -> Path:
    """
    Locate .env regardless of the working directory uvicorn is launched from.
    Walks up from this file's directory until it finds a backend/.env or .env.
    """
    here = Path(__file__).resolve().parent  # app/config/
    # Try: backend/.env  (two levels up from config/)
    candidate = here.parent.parent / ".env"  # backend/.env
    if candidate.exists():
        return candidate
    # Fallback: same dir
    return Path(".env")


def _backend_dir() -> Path:
    """Return the absolute path to the backend/ directory."""
    return Path(__file__).resolve().parent.parent.parent  # app/config/ → app/ → backend/


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_find_env_file()),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── LLM provider ──────────────────────────────────────────────────────────
    # Set LLM_PROVIDER=nim in .env to use the self-hosted Gemma 4 31B NIM.
    # Any other value (or unset) falls back to Gemini.
    llm_provider: str = Field("gemini", description="LLM backend: 'gemini' or 'nim'")

    # ── Gemini ────────────────────────────────────────────────────────────────
    gemini_api_key: str = Field("", description="Google Gemini API key (required when llm_provider=gemini)")
    gemini_model: str = Field("gemini-1.5-flash", description="Gemini model name")
    gemini_temperature: float = Field(0.2, ge=0.0, le=2.0)
    gemini_max_output_tokens: int = Field(2048, ge=128, le=8192)

    # ── NVIDIA NIM ────────────────────────────────────────────────────────────
    # Two modes — controlled by NIM_BASE_URL:
    #
    #   Cloud-hosted (default, no GPU needed):
    #     NIM_BASE_URL=https://integrate.api.nvidia.com/v1
    #     NGC_API_KEY=nvapi-xxxx   ← Personal key from ngc.nvidia.com
    #
    #   Self-hosted (requires ≥64 GB VRAM):
    #     NIM_BASE_URL=http://localhost:8001/v1   (after running nim_deploy.sh)
    #     NGC_API_KEY can be left blank
    #
    ngc_api_key: str = Field(
        "",
        description="NGC Personal API key — required for the cloud-hosted NIM endpoint",
    )
    nim_base_url: str = Field(
        "https://integrate.api.nvidia.com/v1",
        description="NIM endpoint URL — cloud-hosted or self-hosted",
    )
    nim_model: str = Field(
        "deepseek-ai/deepseek-v3.2",
        description="NIM model identifier",
    )
    nim_temperature: float = Field(1.0, ge=0.0, le=2.0)
    nim_top_p: float = Field(0.95, ge=0.0, le=1.0, description="Nucleus sampling probability")
    nim_max_tokens: int = Field(8192, ge=128, le=32768)
    nim_enable_thinking: bool = Field(True, description="Enable DeepSeek thinking mode (chat_template_kwargs={thinking:True}). Thinking tokens arrive in reasoning_content and are not shown to users.")

    # ── Embeddings ─────────────────────────────────────────────────────────────
    embedding_model: str = Field(
        "all-MiniLM-L6-v2", description="Sentence-Transformers model name"
    )
    embedding_dimension: int = Field(384, description="Embedding vector dimension")

    # ── Vector store ───────────────────────────────────────────────────────────
    vector_store_path: Path = Field(
        default_factory=lambda: _backend_dir() / "data" / "vector_store",
        description="Directory to persist FAISS index",
    )
    vector_store_top_k: int = Field(5, ge=1, le=20)

    # ── Chunking ───────────────────────────────────────────────────────────────
    chunk_size: int = Field(512, ge=64, le=2048, description="Tokens per chunk")
    chunk_overlap: int = Field(64, ge=0, le=256)

    # ── Conversation ───────────────────────────────────────────────────────────
    max_conversation_turns: int = Field(
        20, ge=1, description="Max turns kept in memory"
    )

    # ── API ────────────────────────────────────────────────────────────────────
    api_host: str = Field("0.0.0.0")
    api_port: int = Field(8000, ge=1024, le=65535)
    api_prefix: str = Field("/api/v1")
    cors_origins: list[str] = Field(["http://localhost:3000", "http://localhost:5173"])
    debug: bool = Field(False)

    # ── Rate limiting ──────────────────────────────────────────────────────────
    rate_limit_requests: int = Field(60, description="Requests per window")
    rate_limit_window_seconds: int = Field(60)

    # ── Supabase ───────────────────────────────────────────────────────────────
    supabase_url: str = Field("", description="Supabase project URL")
    supabase_anon_key: str = Field("", description="Supabase anon/publishable key")
    supabase_service_role_key: str = Field("", description="Supabase service_role secret key (optional)")

    # ── Clerk ──────────────────────────────────────────────────────────────────
    clerk_secret_key: str = Field("", description="Clerk secret key for JWT verification (sk_test_...)")

    # ── Logging ────────────────────────────────────────────────────────────────
    log_level: str = Field("INFO")

    # ── Neuro-symbolic layer ────────────────────────────────────────────────────
    rules_path: Path = Field(
        default_factory=lambda: _backend_dir() / "app" / "symbolic" / "legal_rules.json",
        description="Path to the symbolic legal rules JSON file",
    )
    corpus_path: Path = Field(
        default_factory=lambda: _backend_dir() / "app" / "symbolic" / "legal_corpus.json",
        description="Path to the seed legal corpus JSON file",
    )
    lawyer_mode: bool = Field(
        True,
        description="Enable lawyer-mode structured five-section reasoning output",
    )

    @field_validator("chunk_overlap")
    @classmethod
    def overlap_less_than_chunk(cls, v: int, info) -> int:
        chunk_size = info.data.get("chunk_size", 512)
        if v >= chunk_size:
            raise ValueError("chunk_overlap must be less than chunk_size")
        return v

    @model_validator(mode="after")
    def validate_provider_keys(self) -> "Settings":
        _NIM_HOSTED = "https://integrate.api.nvidia.com/v1"
        provider = self.llm_provider.lower()

        # Gemini requires its API key
        if provider != "nim" and not self.gemini_api_key:
            raise ValueError(
                "GEMINI_API_KEY is required when LLM_PROVIDER=gemini (the default). "
                "Either set GEMINI_API_KEY in your .env, or set LLM_PROVIDER=nim."
            )

        # NIM cloud-hosted endpoint requires an NGC key
        if provider == "nim" and self.nim_base_url == _NIM_HOSTED and not self.ngc_api_key:
            raise ValueError(
                f"NGC_API_KEY is required when using the cloud-hosted NIM endpoint ({_NIM_HOSTED}).\n"
                "Get a free key at: https://ngc.nvidia.com → Setup → API Keys\n"
                "Then add NGC_API_KEY=nvapi-xxxx to your backend/.env file."
            )

        return self


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the cached application settings singleton."""
    return Settings()
