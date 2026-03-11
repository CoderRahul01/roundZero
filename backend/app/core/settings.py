from __future__ import annotations
print("Loading app.core.settings...")

import os
from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Root directory of the project (one level up from app/)
BASE_DIR = Path(__file__).resolve().parent.parent.parent

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
    print("  Initializing Settings class...")
    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env", 
        case_sensitive=False, 
        extra="ignore"
    )
    print(f"  Settings base dir: {BASE_DIR}")

    # App Core
    environment: str = Field("development", description="Environment label")
    log_level: str = Field("info", description="Logging level for application")
    jwt_secret: str = Field("roundzero-super-secret-key", description="Secret for backend JWT")
    
    # CORS & Security
    cors_allow_origins: list[str] | str = Field(
        default=LOCAL_DEV_ORIGINS,
        description="Comma-separated origins allowed for CORS",
    )
    cors_allow_credentials: bool = True
    allowed_hosts: list[str] | str = Field(default=["*"], description="Trusted hosts")
    
    # Database (Neon / Postgres)
    database_url: str | None = None
    
    # Neon Auth (JWT Verification)
    neon_auth_project_id: str | None = None
    neon_auth_jwks_url: str | None = None
    neon_auth_issuer: str | None = None
    neon_auth_audience: str | None = None

    # Google Gemini & ADK
    # ADK reads GOOGLE_API_KEY and GOOGLE_GENAI_USE_VERTEXAI directly from env.
    # We expose google_api_key here only for validate_setup() and tool usage (e.g. Imagen).
    google_api_key: str | None = Field(None, alias="GOOGLE_API_KEY")
    google_genai_use_vertexai: str = Field("FALSE", alias="GOOGLE_GENAI_USE_VERTEXAI")
    gemini_model: str = Field("gemini-2.5-flash-native-audio-preview-12-2025", alias="GEMINI_MODEL", description="Gemini model for live sessions")

    # Redis (Caching & Rate Limiting)
    upstash_redis_rest_url: str | None = Field(None, alias="UPSTASH_REDIS_REST_URL")
    upstash_redis_rest_token: str | None = Field(None, alias="UPSTASH_REDIS_REST_TOKEN")
    redis_url: str = Field("redis://localhost:6379", alias="REDIS_URL")
    use_redis: bool = Field(True, description="Whether to use Redis for caching")

    # Anthropic Claude (strategic answer evaluation)
    anthropic_api_key: str | None = Field(None, alias="ANTHROPIC_API_KEY")

    # Supermemory (cross-session user memory)
    supermemory_api_key: str | None = Field(None, alias="SUPERMEMORY_API_KEY")
    use_supermemory: bool = Field(False, description="Enable Supermemory for cross-session memory")

    @field_validator("cors_allow_origins", "allowed_hosts", mode="before")
    @classmethod
    def split_csv(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
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

    def validate_setup(self):
        """Simple liveness check for critical keys."""
        if not self.google_api_key:
            raise ValueError("GOOGLE_API_KEY is required for Gemini Live sessions.")


@lru_cache
def get_settings() -> Settings:
    return Settings()
