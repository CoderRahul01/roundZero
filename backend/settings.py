from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parent
LOCAL_DEV_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:3001",
    "http://localhost:5173",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:3001",
    "http://127.0.0.1:5173",
]


def _is_loopback_origin(origin: str) -> bool:
    return origin.startswith("http://localhost:") or origin.startswith("http://127.0.0.1:")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=BASE_DIR / ".env", case_sensitive=False, extra="ignore")

    # App
    environment: str = Field("development", description="Environment label")
    log_level: str = Field("info", description="Logging level for application")
    jwt_secret: str = Field("roundzero-super-secret-key", description="Secret for backend JWT")
    cors_allow_origins: list[str] | str = Field(
        default=["http://localhost:3000", "http://localhost:3001", "http://localhost:5173"],
        description="Comma-separated origins allowed for CORS",
    )
    cors_allow_credentials: bool = True
    allowed_hosts: list[str] | str = Field(default=["*"], description="Trusted hosts")
    rate_limit_max: int = 6
    rate_limit_window_seconds: int = 60
    database_url: str | None = None
    neon_auth_url: str | None = None
    neon_auth_jwks_url: str | None = None
    neon_auth_issuer: str | None = None
    neon_auth_audience: str | None = None
    allow_legacy_hs256_auth: bool = True
    neon_auth_project_id: str | None = None

    # Integrations
    pinecone_api_key: str | None = None
    pinecone_index: str = "interview-questions"
    stream_api_key: str | None = None
    stream_api_secret: str | None = None
    anthropic_api_key: str | None = None
    gemini_api_key: str | None = None
    supermemory_api_key: str | None = None

    # Feature flags
    use_pinecone: bool = False
    use_claude_decision: bool = False
    use_supermemory: bool = False
    use_vision: bool = False
    claude_model: str = "claude-3-5-sonnet-latest"

    @field_validator("cors_allow_origins", "allowed_hosts", mode="before")
    @classmethod
    def split_csv(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @field_validator(
        "neon_auth_url",
        "neon_auth_jwks_url",
        "neon_auth_issuer",
        "neon_auth_audience",
        mode="before",
    )
    @classmethod
    def empty_to_none(cls, value: str | None) -> str | None:
        if isinstance(value, str):
            cleaned = value.strip()
            return cleaned or None
        return value

    def normalized_cors_origins(self) -> list[str]:
        origins = [origin.strip() for origin in self.cors_allow_origins if origin and origin.strip()]
        if not origins:
            return LOCAL_DEV_ORIGINS.copy()

        if any(_is_loopback_origin(origin) for origin in origins):
            for origin in LOCAL_DEV_ORIGINS:
                if origin not in origins:
                    origins.append(origin)

        return origins

    def missing_required(self) -> list[str]:
        required = {
            "ANTHROPIC_API_KEY": self.anthropic_api_key,
            "STREAM_API_KEY": self.stream_api_key,
            "STREAM_API_SECRET": self.stream_api_secret,
        }
        return [key for key, val in required.items() if not val]


@lru_cache
def get_settings() -> Settings:
    return Settings()
