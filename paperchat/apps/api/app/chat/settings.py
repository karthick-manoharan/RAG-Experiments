"""Lazy chat configuration, composed with the ingestion configuration."""

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.ingestion.settings import IngestionSettings
from app.settings import APP_ROOT


class ChatSettings(BaseSettings):
    openrouter_model: str
    openrouter_temperature: float = Field(default=0, ge=0, le=2, allow_inf_nan=False)
    openrouter_max_tokens: int = Field(default=1024, gt=0, le=32768)
    openrouter_timeout_seconds: float = Field(
        default=60, gt=0, le=600, allow_inf_nan=False
    )
    rag_retrieval_timeout_seconds: float = Field(
        default=60, gt=0, le=600, allow_inf_nan=False
    )
    model_config = SettingsConfigDict(
        env_file=APP_ROOT / ".env", env_file_encoding="utf-8", extra="ignore"
    )

    @field_validator("openrouter_model")
    @classmethod
    def nonblank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be blank")
        return value.strip()


def load_settings() -> tuple[ChatSettings, IngestionSettings]:
    return ChatSettings(), IngestionSettings()
