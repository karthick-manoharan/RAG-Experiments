from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from langchain_core.documents import Document
from qdrant_client import models

from app.ingestion import cli, store
from app.ingestion.documents import CHUNKING_VERSION, point_id
from app.ingestion.embeddings import CheckedEmbeddings, embedding_identity, vector_name
from app.ingestion.errors import PipelineError
from app.ingestion.settings import IngestionSettings


def chunk(index=0):
    return Document(
        page_content=f"Attention passage {index}",
        metadata={
            "document_id": "document-hash",
            "source": "paper.pdf",
            "page": 1,
            "chunk_index": index,
            "chunking_version": CHUNKING_VERSION,
        },
    )


@pytest.fixture
def services(monkeypatch, tmp_path):
    for field in IngestionSettings.model_fields:
        monkeypatch.delenv(field.upper(), raising=False)
        monkeypatch.delenv(field, raising=False)
    monkeypatch.setitem(IngestionSettings.model_config, "env_file", tmp_path / "absent")
    settings = IngestionSettings(openrouter_api_key="test-secret")
    provider = Mock()
    provider.embed_query.return_value = [1.0, 0.0, 0.0]
    provider.embed_documents.side_effect = lambda texts: [
        [1.0, 0.0, 0.0] for _ in texts
    ]
    monkeypatch.setattr(
        store, "create_embeddings", lambda _: CheckedEmbeddings(provider)
    )
    client = Mock()
    schema = {}
    points = {}
    events = []

    def create(collection_name, vectors_config):
        schema[collection_name] = vectors_config
        events.append("create")
        return True

    def delete(collection_name):
        del schema[collection_name]
        points.clear()
        events.append("delete")
        return True

    def upsert(collection_name, points: list, wait):
        assert wait is True
        events.append("upsert")
        for point in points:
            stored_points[point.id] = point
        return models.UpdateResult(operation_id=1, status=models.UpdateStatus.COMPLETED)

    stored_points = points
    client.collection_exists.side_effect = lambda name: name in schema
    client.create_collection.side_effect = create
    client.delete_collection.side_effect = delete
    client.get_collection.side_effect = lambda name: SimpleNamespace(
        config=SimpleNamespace(params=SimpleNamespace(vectors=schema[name]))
    )
    client.upsert.side_effect = upsert
    client.query_points.return_value = SimpleNamespace(points=[])
    monkeypatch.setattr(store, "create_client", lambda _: client)
    monkeypatch.setattr(store, "extract_chunks", lambda _: [chunk()])
    return SimpleNamespace(
        settings=settings,
        provider=provider,
        client=client,
        schema=schema,
        points=points,
        events=events,
        path=tmp_path / "paper.pdf",
    )


def test_dense_upserts_are_idempotent(services):
    env = services
    assert store.ingest(env.path, env.settings) == 1
    original = set(env.points)
    assert original == {point_id(chunk())}
    store.ingest(env.path, env.settings)
    assert set(env.points) == original
    env.client.delete_collection.assert_not_called()
    assert len(env.schema) == 1
    vectors = env.schema[env.settings.qdrant_collection]
    assert list(vectors.values())[0].size == 3
    assert list(vectors.values())[0].distance == models.Distance.COSINE
    payload = next(iter(env.points.values())).payload
    assert payload["metadata"]["source"] == "paper.pdf"
    assert payload["metadata"]["page"] == 1
    assert payload["metadata"]["embedding_identity"]["provider"] == "openrouter"


def test_partial_batch_retry(services, monkeypatch):
    env = services
    chunks = [chunk(i) for i in range(65)]
    monkeypatch.setattr(store, "extract_chunks", lambda _: chunks)
    original_upsert = env.client.upsert.side_effect

    def failing_upsert(**kwargs):
        if len(env.points) >= 64:
            raise RuntimeError("network test-secret")
        return original_upsert(**kwargs)

    env.client.upsert.side_effect = failing_upsert
    with pytest.raises(PipelineError, match="64/65") as error:
        store.ingest(env.path, env.settings)
    assert "test-secret" not in str(error.value)
    assert len(env.points) == 64
    env.client.upsert.side_effect = original_upsert
    store.ingest(env.path, env.settings)
    assert len(env.points) == 65


@pytest.mark.parametrize("kind", ["dimensions", "distance", "model", "unnamed"])
def test_schema_mismatch_never_mutates(services, kind):
    env = services
    name = vector_name(embedding_identity(env.settings, 3))
    params = models.VectorParams(
        size=4 if kind == "dimensions" else 3,
        distance=models.Distance.DOT if kind == "distance" else models.Distance.COSINE,
    )
    env.schema[env.settings.qdrant_collection] = (
        params
        if kind == "unnamed"
        else {"other-model" if kind == "model" else name: params}
    )
    with pytest.raises(PipelineError, match="incompatible"):
        store.ingest(env.path, env.settings)
    with pytest.raises(PipelineError, match="incompatible"):
        store.search("attention", env.settings)
    env.client.delete_collection.assert_not_called()
    env.client.create_collection.assert_not_called()
    env.client.upsert.assert_not_called()
    env.client.query_points.assert_not_called()


def test_recreate_scope_and_sequence(services):
    env = services
    store.ingest(env.path, env.settings)
    env.events.clear()
    messages = []
    store.ingest(env.path, env.settings, recreate=True, report=messages.append)
    assert env.events == ["delete", "create", "upsert"]
    assert "ALL points" in messages[0]
    assert env.settings.qdrant_collection in messages[0]
    assert len(env.points) == 1


@pytest.mark.parametrize("failure", ["pdf", "embedding"])
def test_recreate_preflight_prevents_deletion(services, monkeypatch, failure):
    env = services
    store.ingest(env.path, env.settings)
    if failure == "pdf":
        monkeypatch.setattr(
            store, "extract_chunks", Mock(side_effect=PipelineError("missing PDF"))
        )
    else:
        env.provider.embed_query.side_effect = RuntimeError("invalid test-secret")
    with pytest.raises(PipelineError):
        store.ingest(env.path, env.settings, recreate=True)
    env.client.delete_collection.assert_not_called()
    assert len(env.points) == 1


def test_missing_collection_search_does_not_create(services):
    with pytest.raises(PipelineError, match="Ingest first"):
        store.search("attention", services.settings)
    services.client.create_collection.assert_not_called()
    services.client.delete_collection.assert_not_called()
    services.client.upsert.assert_not_called()


def test_dense_search_top_five_is_read_only(services):
    env = services
    store.ingest(env.path, env.settings)
    before = dict(env.points)
    env.client.reset_mock()
    env.client.query_points.return_value = SimpleNamespace(
        points=[
            models.ScoredPoint(
                id=point_id(chunk(i)),
                version=1,
                score=i / 10,
                payload={
                    "page_content": chunk(i).page_content,
                    "metadata": chunk(i).metadata,
                },
            )
            for i in range(7)
        ]
    )
    results = store.search("attention", env.settings)
    assert [score for _, score in results] == [0.6, 0.5, 0.4, 0.3, 0.2]
    assert results[0][0].metadata["source"] == "paper.pdf"
    assert env.client.query_points.call_args.kwargs["limit"] == 5
    assert env.client.query_points.call_args.kwargs["using"].startswith("dense_")
    assert env.points == before
    env.client.create_collection.assert_not_called()
    env.client.delete_collection.assert_not_called()
    env.client.upsert.assert_not_called()


@pytest.mark.parametrize("count", [0, 1, 5])
def test_cli_metadata_and_empty_results(services, monkeypatch, capsys, count):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-secret")
    monkeypatch.setattr(
        store, "search", lambda *args: [(chunk(i), 0.9 - i / 10) for i in range(count)]
    )
    assert cli.main(["search", "multi-head attention"]) == 0
    output = capsys.readouterr().out
    if count:
        assert output.count("Cosine similarity:") == count
        assert (
            "source=paper.pdf page=1 chunk_index=0 document_id=document-hash" in output
        )
        assert "Attention passage 0" in output
    else:
        assert "No matching chunks" in output


@pytest.mark.parametrize(
    "operation", ["collection_exists", "get_collection", "query_points"]
)
def test_search_failure_redacts_credentials(services, monkeypatch, capsys, operation):
    env = services
    store.ingest(env.path, env.settings)
    getattr(env.client, operation).side_effect = RuntimeError("remote test-secret")
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-secret")
    assert cli.main(["search", "attention"]) == 1
    error = capsys.readouterr().err
    assert "Qdrant" in error
    assert "test-secret" not in error


def test_client_local_cloud_environment_only(monkeypatch):
    factory = Mock()
    monkeypatch.setattr(store, "QdrantClient", factory)
    local = IngestionSettings(_env_file=None, openrouter_api_key="test")
    store.create_client(local)
    assert factory.call_args.kwargs["url"] == "http://localhost:6333"
    assert factory.call_args.kwargs["api_key"] is None
    cloud = IngestionSettings(
        _env_file=None,
        openrouter_api_key="test",
        qdrant_url="https://cluster.example.com:6333",
        qdrant_api_key="cloud-secret",
    )
    store.create_client(cloud)
    assert factory.call_args.kwargs["url"] == cloud.qdrant_url
    assert factory.call_args.kwargs["api_key"] == "cloud-secret"


def test_cli_missing_pdf_no_remote_mutation(services, monkeypatch, capsys):
    from app.ingestion.documents import extract_chunks

    monkeypatch.setattr(store, "extract_chunks", extract_chunks)
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-secret")
    assert cli.main(["ingest", str(services.path), "--recreate"]) == 1
    assert "not found" in capsys.readouterr().err
    services.client.delete_collection.assert_not_called()
    services.client.upsert.assert_not_called()
