from fastapi.testclient import TestClient

from app.main import app


def test_local_preflight_and_disallowed_origins():
    with TestClient(app) as client:
        for origin, allowed in [
            ("http://localhost:3000", True),
            ("https://other.example", False),
        ]:
            response = client.options(
                "/api/v1/chat/stream",
                headers={
                    "Origin": origin,
                    "Access-Control-Request-Method": "POST",
                    "Access-Control-Request-Headers": "content-type",
                },
            )
            assert (response.status_code == 200) is allowed
            assert (
                response.headers.get("access-control-allow-origin") == origin
            ) is allowed
            assert "access-control-allow-credentials" not in response.headers


def test_validation_errors_are_readable():
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/chat/stream",
            json={"question": ""},
            headers={"Origin": "http://localhost:3000"},
        )
        assert response.status_code == 422
        assert (
            response.headers["access-control-allow-origin"] == "http://localhost:3000"
        )


def test_stream_and_service_errors_are_readable(monkeypatch):
    from app.chat import router, service

    async def unavailable(question):
        raise service.ChatError(
            503, "configuration_unavailable", "Chat is not configured."
        )

    monkeypatch.setattr(router, "prepare", unavailable)
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/chat/stream",
            json={"question": "q"},
            headers={"Origin": "http://localhost:3000"},
        )
        assert response.status_code == 503
        assert (
            response.headers["access-control-allow-origin"] == "http://localhost:3000"
        )

    async def prepared(question):
        from app.chat.settings import ChatSettings

        return service.Prepared(
            ChatSettings(openrouter_model="test", _env_file=None), [], "test", 0
        )

    monkeypatch.setattr(router, "prepare", prepared)
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/chat/stream",
            json={"question": "q"},
            headers={"Origin": "http://localhost:3000"},
        )
        assert response.status_code == 200
        assert "event: done" in response.text
        assert (
            response.headers["access-control-allow-origin"] == "http://localhost:3000"
        )
