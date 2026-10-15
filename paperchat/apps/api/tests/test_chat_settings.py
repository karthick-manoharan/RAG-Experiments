import asyncio

import httpx
import pytest
from pydantic import ValidationError

from app.chat.settings import ChatSettings, load_settings
from app.main import app
from app.settings import APP_ROOT


def test_settings_boundary_and_precedence(monkeypatch, tmp_path):
    (tmp_path / ".env").write_text("OPENROUTER_MODEL=wrong\n")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("OPENROUTER_MODEL", " selected/model ")
    monkeypatch.setenv("OPENROUTER_API_KEY", "sentinel-key")
    chat, ingestion = load_settings()
    assert chat.openrouter_model == "selected/model"
    assert ChatSettings.model_config["env_file"] == APP_ROOT / ".env"
    assert "sentinel-key" not in repr(ingestion)
    dotenv = tmp_path / "app.env"
    dotenv.write_text("OPENROUTER_MODEL=dotenv/model\n")
    assert ChatSettings(_env_file=dotenv).openrouter_model == "selected/model"


@pytest.mark.parametrize(
    "field,value",
    [
        ("openrouter_model", " "),
        ("openrouter_temperature", -1),
        ("openrouter_temperature", 3),
        ("openrouter_temperature", float("nan")),
        ("openrouter_max_tokens", 0),
        ("openrouter_max_tokens", 32769),
        ("openrouter_max_tokens", 1.5),
        ("openrouter_timeout_seconds", 0),
        ("openrouter_timeout_seconds", 601),
        ("openrouter_timeout_seconds", float("inf")),
        ("rag_retrieval_timeout_seconds", 0),
        ("rag_retrieval_timeout_seconds", float("nan")),
    ],
)
def test_invalid_settings(field, value):
    with pytest.raises(ValidationError):
        ChatSettings(_env_file=None, **{"openrouter_model": "test", field: value})


def test_health_without_chat(monkeypatch):
    monkeypatch.delenv("OPENROUTER_MODEL", raising=False)

    async def run():
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            assert (await client.get("/health")).json() == {"status": "ok"}

    asyncio.run(run())


@pytest.mark.parametrize("configured", [False, True])
def test_startup_and_safe_configuration_failure(monkeypatch, caplog, configured):
    import logging

    from fastapi.testclient import TestClient

    from app.main import create_app
    from app.settings import Settings

    monkeypatch.setitem(ChatSettings.model_config, "env_file", None)
    from app.ingestion.settings import IngestionSettings

    monkeypatch.setitem(IngestionSettings.model_config, "env_file", None)
    for key in ("OPENROUTER_MODEL", "OPENROUTER_API_KEY", "QDRANT_API_KEY"):
        monkeypatch.delenv(key, raising=False)
    if configured:
        monkeypatch.setenv("OPENROUTER_MODEL", "test/model")
        monkeypatch.setenv("OPENROUTER_API_KEY", "sentinel-secret")
    with (
        caplog.at_level(logging.INFO),
        TestClient(create_app(Settings(_env_file=None))) as client,
    ):
        assert client.get("/health").json() == {"status": "ok"}
        monkeypatch.setenv("OPENROUTER_MAX_TOKENS", "sentinel-invalid-value")
        response = client.post("/api/v1/chat/stream", json={"question": "q"})
        assert response.status_code == 503
        assert response.json()["detail"]["code"] == "configuration_unavailable"
        assert "sentinel" not in response.text
    assert "sentinel" not in caplog.text
