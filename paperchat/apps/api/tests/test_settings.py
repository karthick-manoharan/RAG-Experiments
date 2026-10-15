from pathlib import Path

import pytest

from app.settings import APP_ROOT, Settings


@pytest.fixture(autouse=True)
def clear_app_name(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("APP_NAME", raising=False)
    monkeypatch.delenv("app_name", raising=False)


def test_defaults_without_dotenv(tmp_path: Path) -> None:
    settings = Settings(_env_file=tmp_path / "missing.env")
    assert settings.app_name == "PaperChat API"


def test_dotenv_loading_ignores_unrelated_keys(tmp_path: Path) -> None:
    dotenv = tmp_path / ".env"
    dotenv.write_text("APP_NAME=Local PaperChat\nUNRELATED=value\n")
    assert Settings(_env_file=dotenv).app_name == "Local PaperChat"


def test_environment_overrides_dotenv(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    dotenv = tmp_path / ".env"
    dotenv.write_text("APP_NAME=Local PaperChat\n")
    monkeypatch.setenv("APP_NAME", "Hosted PaperChat")
    assert Settings(_env_file=dotenv).app_name == "Hosted PaperChat"


def test_dotenv_path_is_absolute_and_app_local(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert Settings.model_config["env_file"] == APP_ROOT / ".env"
    assert APP_ROOT == Path(__file__).resolve().parents[1]
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text("APP_NAME=Wrong directory\n")
    assert Settings(_env_file=tmp_path / "missing.env").app_name == "PaperChat API"


def test_setting_controls_fastapi_title(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import importlib

    import app.main

    monkeypatch.setitem(Settings.model_config, "env_file", tmp_path / "missing.env")
    monkeypatch.setenv("APP_NAME", "Configured PaperChat")
    try:
        assert importlib.reload(app.main).app.title == "Configured PaperChat"
    finally:
        monkeypatch.delenv("APP_NAME")
        importlib.reload(app.main)


@pytest.mark.parametrize(
    "origin",
    [
        "*",
        "https://*.vercel.app",
        "https://example.com/",
        "https://example.com/path",
        "https://user:pass@example.com",
        "https://example.com?x=1",
        "https://example.com#fragment",
        "file:///tmp",
        "https://example.com:bad",
        "",
    ],
)
def test_invalid_cors_origins(origin):
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        Settings(_env_file=None, cors_allowed_origins=[origin])


def test_cors_json_environment(monkeypatch):
    monkeypatch.setenv(
        "CORS_ALLOWED_ORIGINS",
        '["https://paperchat.vercel.app","http://localhost:3000"]',
    )
    assert Settings(_env_file=None).cors_allowed_origins == [
        "https://paperchat.vercel.app",
        "http://localhost:3000",
    ]
