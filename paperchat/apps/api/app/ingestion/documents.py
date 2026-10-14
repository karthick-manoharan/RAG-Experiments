"""Page-aware extraction and repeatable chunk identities."""

import hashlib
import json
from pathlib import Path
from uuid import UUID, uuid5

import pymupdf
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.ingestion.errors import PipelineError

CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200
CHUNKING_VERSION = "pymupdf-text-recursive-v1-1000-200"
POINT_NAMESPACE = UUID("6e42642a-3273-55a8-9512-cbff157ed494")


def extract_chunks(path: Path) -> list[Document]:
    try:
        data = path.read_bytes()
    except FileNotFoundError:
        raise PipelineError(
            f"PDF file not found: {path}. Check the input path."
        ) from None
    except OSError:
        raise PipelineError(
            f"Cannot read PDF: {path}. Check file permissions."
        ) from None

    document_id = hashlib.sha256(data).hexdigest()
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        length_function=len,
        separators=["\n\n", "\n", " ", ""],
        is_separator_regex=False,
    )
    chunks = []
    try:
        with pymupdf.open(stream=data, filetype="pdf") as pdf:
            if pdf.needs_pass:
                raise PipelineError("PDF is encrypted. Provide an unencrypted copy.")
            for page_number, page in enumerate(pdf, start=1):
                text = page.get_text("text")
                for chunk_index, text_chunk in enumerate(splitter.split_text(text)):
                    if text_chunk.strip():
                        chunks.append(
                            Document(
                                page_content=text_chunk,
                                metadata={
                                    "document_id": document_id,
                                    "source": path.name,
                                    "page": page_number,
                                    "chunk_index": chunk_index,
                                    "chunking_version": CHUNKING_VERSION,
                                },
                            )
                        )
    except PipelineError:
        raise
    except Exception:
        raise PipelineError(
            f"Cannot extract PDF: {path}. Check that it is a valid readable PDF."
        ) from None
    if not chunks:
        raise PipelineError("PDF has no extractable text. OCR is not supported.")
    return chunks


def point_id(chunk: Document) -> str:
    identity = [
        chunk.metadata["document_id"],
        chunk.metadata["chunking_version"],
        chunk.metadata["page"],
        chunk.metadata["chunk_index"],
        hashlib.sha256(chunk.page_content.encode()).hexdigest(),
    ]
    return str(uuid5(POINT_NAMESPACE, json.dumps(identity, separators=(",", ":"))))
