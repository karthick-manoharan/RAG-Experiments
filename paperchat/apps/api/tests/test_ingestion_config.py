from unittest.mock import Mock

import pytest
from pydantic import ValidationError

from app.ingestion import cli, embeddings
from app.ingestion.embeddings import CheckedEmbeddings
from app.ingestion.errors import PipelineError
from app.ingestion.settings import EMBEDDINGS_ENDPOINT, IngestionSettings
from app.settings import APP_ROOT


@pytest.fixture(autouse=True)
def isolated_config(monkeypatch, tmp_path):
    for name in IngestionSettings.model_fields:
        monkeypatch.delenv(name.upper(), raising=False)
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setitem(IngestionSettings.model_config, "env_file", tmp_path / "absent")


def test_defaults_and_required_key():
    with pytest.raises(ValidationError):
        IngestionSettings()
    settings = IngestionSettings(openrouter_api_key="test-secret")
    assert settings.embeddings_model == "openai/text-embedding-3-small"
    assert settings.embeddings_provider == "openrouter"
    assert settings.qdrant_url == "http://localhost:6333"
    assert settings.qdrant_collection == "paperchat-papers"
    assert "test-secret" not in repr(settings)


def test_app_local_dotenv_and_precedence(tmp_path, monkeypatch):
    dotenv = tmp_path / ".env"
    dotenv.write_text("OPENROUTER_API_KEY=test\nQDRANT_COLLECTION=dotenv\n")
    monkeypatch.setenv("QDRANT_COLLECTION", "environment")
    assert IngestionSettings(_env_file=dotenv).qdrant_collection == "environment"
    monkeypatch.chdir(tmp_path)
    assert APP_ROOT.is_absolute()
    monkeypatch.setitem(
        IngestionSettings.model_config, "env_file", tmp_path / "app" / ".env"
    )
    with pytest.raises(ValidationError):
        IngestionSettings()
    assert IngestionSettings.model_config["env_file"].is_absolute()


@pytest.mark.parametrize(
    "kwargs",
    [
        {"embeddings_provider": "unsupported"},
        {"embeddings_model": " "},
        {"openrouter_api_key": " "},
        {"qdrant_collection": " "},
        {"qdrant_url": "file:///tmp/store"},
        {"qdrant_url": "https://user:secret@example.com"},
        {"qdrant_url": "https://example.com?api_key=secret"},
        {"qdrant_url": "http://localhost:bad"},
    ],
)
def test_invalid_config(kwargs):
    with pytest.raises(ValidationError):
        IngestionSettings(**({"openrouter_api_key": "test"} | kwargs))


def test_optional_qdrant_key():
    assert (
        IngestionSettings(openrouter_api_key="test", qdrant_api_key="").qdrant_api_key
        is None
    )


def test_explicit_provider_endpoint_and_credentials(monkeypatch):
    monkeypatch.setenv("CHAT_API_KEY", "chat-secret")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://chat.example.com")
    factory = Mock()
    monkeypatch.setattr(embeddings, "OpenAIEmbeddings", factory)
    settings = IngestionSettings(openrouter_api_key="embedding-secret")
    embeddings.create_embeddings(settings)
    kwargs = factory.call_args.kwargs
    assert kwargs["base_url"] == EMBEDDINGS_ENDPOINT
    assert kwargs["api_key"].get_secret_value() == "embedding-secret"
    assert kwargs["model"] == settings.embeddings_model
    assert kwargs["request_timeout"] == 30
    assert kwargs["max_retries"] == 2
    assert kwargs["check_embedding_ctx_length"] is False
    assert kwargs["model_kwargs"]["encoding_format"] == "float"


def test_real_integration_sends_text_to_embeddings_endpoint(monkeypatch):
    import json

    import openai
    from langchain_openai import OpenAIEmbeddings

    requests = []

    # Use the HTTP library installed with this SDK, through its client constructor.
    # No network calls are made: the transport supplies an embeddings response.
    http_module = __import__(
        openai.DefaultHttpxClient.__mro__[1].__module__.split(".")[0]
    )

    def respond(request):
        requests.append(request)
        payload = json.loads(request.content)
        return http_module.Response(
            200,
            json={
                "object": "list",
                "model": payload["model"],
                "data": [
                    {
                        "object": "embedding",
                        "index": index,
                        "embedding": [0.1, 0.2, 0.3],
                    }
                    for index, _ in enumerate(payload["input"])
                ],
                "usage": {"prompt_tokens": 1, "total_tokens": 1},
            },
        )

    with openai.DefaultHttpxClient(
        transport=http_module.MockTransport(respond)
    ) as http:

        def factory(**kwargs):
            return OpenAIEmbeddings(http_client=http, **kwargs)

        monkeypatch.setattr(embeddings, "OpenAIEmbeddings", factory)
        checked = embeddings.create_embeddings(
            IngestionSettings(openrouter_api_key="embedding-secret")
        )
        assert (
            checked.embed_documents(["multi-head attention", "transformer"])
            == [[0.1, 0.2, 0.3]] * 2
        )
    request = requests[0]
    assert str(request.url) == "https://openrouter.ai/api/v1/embeddings"
    assert request.headers["authorization"] == "Bearer embedding-secret"
    payload = json.loads(request.content)
    assert payload["model"] == "openai/text-embedding-3-small"
    assert payload["input"] == ["multi-head attention", "transformer"]
    assert payload["encoding_format"] == "float"


@pytest.mark.parametrize("method", ["embed_query", "embed_documents"])
def test_provider_failure_is_safe(method):
    provider = Mock()
    getattr(provider, method).side_effect = RuntimeError("invalid test-secret")
    checked = CheckedEmbeddings(provider)
    with pytest.raises(PipelineError, match="OPENROUTER_API_KEY") as error:
        getattr(checked, method)("query" if method == "embed_query" else ["document"])
    assert "test-secret" not in str(error.value)


@pytest.mark.parametrize(
    "vectors", [[], [[]], [[float("nan")]], [[float("inf")]], [[1], [1, 2]]]
)
def test_invalid_vectors(vectors):
    provider = Mock()
    provider.embed_documents.return_value = vectors
    with pytest.raises(PipelineError):
        CheckedEmbeddings(provider).embed_documents(["x"] * max(1, len(vectors)))


def test_inconsistent_dimension_across_calls():
    provider = Mock()
    provider.embed_query.return_value = [1.0, 2.0]
    provider.embed_documents.return_value = [[1.0]]
    checked = CheckedEmbeddings(provider)
    checked.embed_query("probe")
    with pytest.raises(PipelineError, match="dimensions"):
        checked.embed_documents(["document"])


def test_blank_query_needs_no_credentials(capsys):
    assert cli.main(["search", "  "]) == 1
    assert "blank" in capsys.readouterr().err


def test_configuration_error_redacts_input(monkeypatch, capsys):
    monkeypatch.setenv("EMBEDDINGS_PROVIDER", "test-secret")
    assert cli.main(["search", "attention"]) == 1
    error = capsys.readouterr().err
    assert "EMBEDDINGS_PROVIDER" in error
    assert "test-secret" not in error


def test_help_and_search_recreate(capsys):
    with pytest.raises(SystemExit) as result:
        cli.main(["--help"])
    assert result.value.code == 0
    assert "ingest" in capsys.readouterr().out
    with pytest.raises(SystemExit) as result:
        cli.main(["search", "attention", "--recreate"])
    assert result.value.code == 2
