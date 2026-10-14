import importlib
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.settings import Settings


def test_health_without_credentials(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("APP_NAME", raising=False)
    monkeypatch.delenv("app_name", raising=False)
    monkeypatch.setitem(Settings.model_config, "env_file", tmp_path / "missing.env")
    main = importlib.import_module("app.main")
    with TestClient(main.app) as client:
        response = client.get("/health")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"
    assert response.json() == {"status": "ok"}
    assert response.text == '{"status":"ok"}'
