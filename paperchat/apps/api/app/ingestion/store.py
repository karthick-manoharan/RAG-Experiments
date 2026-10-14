"""Explicit collection lifecycle and LangChain dense indexing/retrieval."""

from collections.abc import Callable
from contextlib import suppress
from pathlib import Path

from langchain_core.documents import Document
from langchain_qdrant import QdrantVectorStore, RetrievalMode
from qdrant_client import QdrantClient, models

from app.ingestion.documents import extract_chunks, point_id
from app.ingestion.embeddings import (
    CheckedEmbeddings,
    create_embeddings,
    embedding_identity,
    vector_name,
)
from app.ingestion.errors import IndexUnavailable, PipelineError, qdrant_request
from app.ingestion.settings import IngestionSettings

BATCH_SIZE = 64


def create_client(settings: IngestionSettings) -> QdrantClient:
    with qdrant_request():
        return QdrantClient(
            url=settings.qdrant_url,
            api_key=(
                settings.qdrant_api_key.get_secret_value()
                if settings.qdrant_api_key
                else None
            ),
            timeout=30,
        )


def validate_collection(
    client: QdrantClient, collection: str, name: str, dimension: int
) -> None:
    with qdrant_request():
        vectors = client.get_collection(collection).config.params.vectors
    if (
        not isinstance(vectors, dict)
        or name not in vectors
        or vectors[name].size != dimension
        or vectors[name].distance != models.Distance.COSINE
    ):
        raise IndexUnavailable(
            f"Collection {collection!r} is incompatible with the configured "
            "embedding model, dimensions, or cosine distance. Choose a compatible "
            "QDRANT_COLLECTION or explicitly rebuild with ingest --recreate "
            "(deletes every point in that collection)."
        )


def open_store(
    client: QdrantClient,
    collection: str,
    embeddings: CheckedEmbeddings,
    name: str,
) -> QdrantVectorStore:
    # Schema is checked above, including model identity. Avoid the integration's
    # extra dimension probe; every actual vector is validated by CheckedEmbeddings.
    return QdrantVectorStore(
        client=client,
        collection_name=collection,
        embedding=embeddings,
        retrieval_mode=RetrievalMode.DENSE,
        vector_name=name,
        distance=models.Distance.COSINE,
        validate_collection_config=False,
    )


def close_client(client: QdrantClient) -> None:
    # Cleanup failure must not mask the original diagnostic or an acknowledged write.
    with suppress(Exception):
        client.close()


def ingest(
    path: Path,
    settings: IngestionSettings,
    *,
    recreate: bool = False,
    report: Callable[[str], None] = print,
) -> int:
    chunks = extract_chunks(path)
    embeddings = create_embeddings(settings)
    dimension = len(embeddings.embed_query(chunks[0].page_content))
    identity = embedding_identity(settings, dimension)
    name = vector_name(identity)
    for chunk in chunks:
        chunk.metadata["embedding_identity"] = identity
    client = create_client(settings)
    completed = 0
    try:
        with qdrant_request():
            exists = client.collection_exists(settings.qdrant_collection)
            if recreate and exists:
                report(
                    f"Recreating {settings.qdrant_collection!r} at "
                    f"{settings.qdrant_url}: deleting ALL points in this collection."
                )
                if not client.delete_collection(settings.qdrant_collection):
                    raise PipelineError(
                        "Qdrant did not acknowledge collection deletion."
                    )
                exists = False
            if not exists:
                if not client.create_collection(
                    collection_name=settings.qdrant_collection,
                    vectors_config={
                        name: models.VectorParams(
                            size=dimension, distance=models.Distance.COSINE
                        )
                    },
                ):
                    raise PipelineError(
                        "Qdrant did not acknowledge collection creation."
                    )
        validate_collection(client, settings.qdrant_collection, name, dimension)
        store = open_store(client, settings.qdrant_collection, embeddings, name)
        try:
            for start in range(0, len(chunks), BATCH_SIZE):
                batch = chunks[start : start + BATCH_SIZE]
                with qdrant_request():
                    store.add_documents(
                        batch,
                        ids=[point_id(chunk) for chunk in batch],
                        batch_size=BATCH_SIZE,
                        wait=True,
                    )
                completed += len(batch)
        except PipelineError as error:
            raise PipelineError(
                f"{error} Ingestion incomplete: {completed}/{len(chunks)} chunks "
                "acknowledged in completed batches; the last batch may be partially "
                "stored. Rerun the same ingest command without --recreate "
                "to retry safely."
            ) from None
        report(
            f"Ingested {len(chunks)} chunks into {settings.qdrant_collection!r}; "
            f"document_id={chunks[0].metadata['document_id']}; source={path.name}."
        )
        return len(chunks)
    finally:
        close_client(client)


def search(query: str, settings: IngestionSettings) -> list[tuple[Document, float]]:
    if not query.strip():
        raise PipelineError("Search query must not be blank.")
    client = create_client(settings)
    try:
        with qdrant_request():
            exists = client.collection_exists(settings.qdrant_collection)
        if not exists:
            raise IndexUnavailable(
                f"Collection {settings.qdrant_collection!r} does not exist. "
                "Ingest first."
            )
        embeddings = create_embeddings(settings)
        dimension = len(embeddings.embed_query(query))
        name = vector_name(embedding_identity(settings, dimension))
        validate_collection(client, settings.qdrant_collection, name, dimension)
        store = open_store(client, settings.qdrant_collection, embeddings, name)
        with qdrant_request():
            results = store.similarity_search_with_score(query, k=5)
        return sorted(results, key=lambda item: item[1], reverse=True)[:5]
    finally:
        close_client(client)
