"""Operator-facing errors that never interpolate remote exception contents."""

from collections.abc import Iterator
from contextlib import contextmanager


class PipelineError(Exception):
    """A safe diagnostic suitable for CLI output."""


class IndexUnavailable(PipelineError):
    """A missing or incompatible read-only index."""


class EmbeddingsFailure(PipelineError):
    """An embedding provider failure."""


class QdrantFailure(PipelineError):
    """A vector service failure."""


@contextmanager
def qdrant_request() -> Iterator[None]:
    try:
        yield
    except PipelineError:
        raise
    except Exception:
        raise QdrantFailure(
            "Qdrant request failed. Check QDRANT_URL, QDRANT_API_KEY, network "
            "access, and collection permissions."
        ) from None
