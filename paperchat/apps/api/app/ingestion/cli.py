"""Standalone CLI; arguments and safe diagnostics are the public interface."""

import argparse
import sys
from pathlib import Path

from pydantic import ValidationError

from app.ingestion.errors import PipelineError
from app.ingestion.settings import IngestionSettings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Index a paper or search its passages."
    )
    commands = parser.add_subparsers(dest="command", required=True)
    ingest_parser = commands.add_parser(
        "ingest", help="Extract, embed, and upsert a PDF"
    )
    ingest_parser.add_argument(
        "pdf", type=Path, help="Local PDF path (relative to cwd)"
    )
    ingest_parser.add_argument(
        "--recreate",
        action="store_true",
        help="Delete ALL points in the configured collection and rebuild it",
    )
    search_parser = commands.add_parser("search", help="Return the top five passages")
    search_parser.add_argument("query", help="Nonblank text query")
    args = parser.parse_args(argv)
    try:
        if args.command == "search" and not args.query.strip():
            raise PipelineError("Search query must not be blank.")
        settings = IngestionSettings()
        # Help/argument validation need no heavy integration imports or clients.
        from app.ingestion.store import ingest, search

        if args.command == "ingest":
            ingest(args.pdf, settings, recreate=args.recreate)
        else:
            results = search(args.query, settings)
            if not results:
                print("No matching chunks in the collection.")
            for index, (chunk, score) in enumerate(results, start=1):
                metadata = chunk.metadata
                print(f"\n{index}. Cosine similarity: {score:.6f} (higher is closer)")
                print(
                    f"source={metadata['source']} page={metadata['page']} "
                    f"chunk_index={metadata['chunk_index']} "
                    f"document_id={metadata['document_id']}"
                )
                print(chunk.page_content)
        return 0
    except ValidationError as error:
        # Pydantic errors can contain secret input values; print field names only.
        fields = sorted({str(item["loc"][0]).upper() for item in error.errors()})
        print(
            "Configuration error: check "
            + ", ".join(fields)
            + ". Supported EMBEDDINGS_PROVIDER: openrouter. Configure apps/api/.env "
            "or process environment; embeddings need their own API key.",
            file=sys.stderr,
        )
        return 1
    except PipelineError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
