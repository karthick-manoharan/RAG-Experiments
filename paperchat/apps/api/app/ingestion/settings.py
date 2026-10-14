"""CLI-only settings; the repository-root dotenv is intentionally not read."""

from typing import Literal
from urllib.parse import urlsplit

from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.settings import APP_ROOT

EMBEDDINGS_ENDPOINT = "https://openrouter.ai/api/v1"


class IngestionSettings(BaseSettings):
    embeddings_provider: Literal["openrouter"] = "openrouter"
    embeddings_model: str = "openai/text-embedding-3-small"
    openrouter_api_key: SecretStr
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: SecretStr | None = None
    qdrant_collection: str = "paperchat-papers"

    model_config = SettingsConfigDict(
        env_file=APP_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator("embeddings_model", "qdrant_collection")
    @classmethod
    def nonblank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be blank")
        return value.strip()

    @field_validator("openrouter_api_key")
    @classmethod
    def required_key(cls, value: SecretStr) -> SecretStr:
        if not value.get_secret_value().strip():
            raise ValueError("must not be blank")
        return value

    @field_validator("qdrant_api_key", mode="before")
    @classmethod
    def optional_key(cls, value: object) -> object:
        return None if value == "" else value

    @field_validator("qdrant_url")
    @classmethod
    def http_url(cls, value: str) -> str:
        url = urlsplit(value)
        if (
            url.scheme not in {"http", "https"}
            or not url.hostname
            or url.username is not None
            or url.password is not None
            or url.query
            or url.fragment
        ):
            raise ValueError("use an HTTP(S) URL without credentials or query")
        _ = url.port  # Reject malformed ports before constructing a client.
        return value.rstrip("/")
