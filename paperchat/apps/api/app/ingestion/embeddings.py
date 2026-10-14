"""Dedicated API embeddings with validation at the service boundary."""

import hashlib
import json
import math

from langchain_core.embeddings import Embeddings
from langchain_openai import OpenAIEmbeddings

from app.ingestion.errors import EmbeddingsFailure, PipelineError
from app.ingestion.settings import EMBEDDINGS_ENDPOINT, IngestionSettings


class CheckedEmbeddings(Embeddings):
    """Validate all vectors and convert provider failures to safe diagnostics."""

    def __init__(self, provider: Embeddings):
        self.provider = provider
        self.dimension: int | None = None

    def _validate(self, vectors: list[list[float]], count: int) -> list[list[float]]:
        if len(vectors) != count or not vectors:
            raise EmbeddingsFailure("Embeddings API returned an invalid vector count.")
        for vector in vectors:
            if not vector or not all(math.isfinite(value) for value in vector):
                raise EmbeddingsFailure(
                    "Embeddings API returned an empty/nonfinite vector."
                )
            if self.dimension is None:
                self.dimension = len(vector)
            if len(vector) != self.dimension:
                raise EmbeddingsFailure(
                    "Embeddings API returned inconsistent dimensions."
                )
        return vectors

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        try:
            return self._validate(self.provider.embed_documents(texts), len(texts))
        except PipelineError:
            raise
        except Exception:
            raise self._failure() from None

    def embed_query(self, text: str) -> list[float]:
        try:
            return self._validate([self.provider.embed_query(text)], 1)[0]
        except PipelineError:
            raise
        except Exception:
            raise self._failure() from None

    @staticmethod
    def _failure() -> PipelineError:
        return EmbeddingsFailure(
            "Embeddings API request failed. Check OPENROUTER_API_KEY, "
            "EMBEDDINGS_MODEL, account quota, and network access."
        )


def create_embeddings(settings: IngestionSettings) -> CheckedEmbeddings:
    # Explicit endpoint/key isolate embeddings from future chat configuration.
    try:
        provider = OpenAIEmbeddings(
            model=settings.embeddings_model,
            api_key=settings.openrouter_api_key,
            base_url=EMBEDDINGS_ENDPOINT,
            request_timeout=30,
            max_retries=2,
            check_embedding_ctx_length=False,
            model_kwargs={"encoding_format": "float"},
        )
    except Exception:
        raise CheckedEmbeddings._failure() from None
    return CheckedEmbeddings(provider)


def embedding_identity(settings: IngestionSettings, dimension: int) -> dict:
    return {
        "version": 1,
        "provider": settings.embeddings_provider,
        "model": settings.embeddings_model,
        "endpoint": EMBEDDINGS_ENDPOINT,
        "dimensions": dimension,
    }


def vector_name(identity: dict) -> str:
    canonical = json.dumps(identity, sort_keys=True, separators=(",", ":"))
    return "dense_" + hashlib.sha256(canonical.encode()).hexdigest()
