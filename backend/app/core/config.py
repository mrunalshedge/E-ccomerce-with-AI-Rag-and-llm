"""Application settings, loaded from environment variables and ``backend/.env``."""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import URL

# backend/.env, resolved from this file so it works regardless of the current directory.
ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ENV_FILE, env_file_encoding="utf-8", extra="ignore")

    app_name: str = "ShopSense"
    environment: str = "development"
    api_v1_prefix: str = "/api/v1"

    # PostgreSQL — no defaults for credentials: they must come from the environment.
    postgres_user: str
    postgres_password: str
    postgres_host: str = "localhost"
    postgres_port: int = 5433
    postgres_db: str = "shopsense"
    postgres_test_db: str = "shopsense_test"
    # "require" for cloud Postgres (Neon, Supabase); "disable" for local Docker.
    postgres_ssl: Literal["disable", "require"] = "disable"
    sql_echo: bool = False

    redis_url: str = "redis://localhost:6379/0"
    # Secret password for the seeded demo *seller and admin* accounts (customers use a public one).
    seed_staff_password: SecretStr | None = None
    # Sliding-window rate limits on login, search and AI endpoints (tests turn this off).
    rate_limit_enabled: bool = True
    # Number of reverse proxies in front of the app that append to X-Forwarded-For (0 locally,
    # usually 1 on Render / Hugging Face / Fly). Used to find the real client IP for rate limits.
    trusted_proxy_hops: int = Field(default=0, ge=0, le=5)

    jwt_secret_key: str = Field(min_length=32)
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = Field(default=60, gt=0)
    # bcrypt work factor. 12 for real use; tests lower it to 4 so they run fast.
    bcrypt_rounds: int = Field(default=12, ge=4, le=16)

    cors_origins: list[str] = ["http://localhost:5173"]

    # --- AI ---
    # Gemini (free tier from https://aistudio.google.com/apikey). The assistant is disabled without a key.
    gemini_api_key: SecretStr | None = None
    # Lite is fast (~1.2 s) and reliable on the free tier; the full model is the fallback.
    gemini_model: str = "gemini-flash-lite-latest"
    gemini_fallback_model: str | None = "gemini-flash-latest"
    assistant_timeout_seconds: float = Field(default=45, gt=0)
    # "fastembed" runs a local multilingual model; "fake" is a fast deterministic stand-in for tests.
    embedding_backend: Literal["fastembed", "fake"] = "fastembed"
    embedding_model: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    # Outside the project folder so the ~250 MB model isn't synced by OneDrive or committed.
    embedding_cache_dir: Path = Path.home() / ".cache" / "shopsense" / "fastembed"

    def _db_url(self, database: str) -> URL:
        # URL.create escapes special characters in the password for us.
        return URL.create(
            drivername="postgresql+asyncpg",
            username=self.postgres_user,
            password=self.postgres_password,
            host=self.postgres_host,
            port=self.postgres_port,
            database=database,
            query={"ssl": "require"} if self.postgres_ssl == "require" else {},
        )

    @property
    def database_url(self) -> URL:
        return self._db_url(self.postgres_db)

    @property
    def test_database_url(self) -> URL:
        return self._db_url(self.postgres_test_db)


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]  # required fields come from env
