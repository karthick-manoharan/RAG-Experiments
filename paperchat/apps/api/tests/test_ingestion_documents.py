import hashlib
from pathlib import Path
from uuid import UUID

import pymupdf
import pytest

from app.ingestion import documents
from app.ingestion.documents import extract_chunks, point_id
from app.ingestion.errors import PipelineError


@pytest.fixture
def paper(tmp_path):
    path = tmp_path / "paper.pdf"
    with pymupdf.open() as pdf:
        pdf.new_page().insert_text((72, 72), "Multi-head attention uses several heads.")
        pdf.new_page()
        pdf.new_page().insert_text((72, 72), "Multi-head attention uses several heads.")
        pdf.save(path)
    return path


def test_pages_metadata_and_ids(paper):
    chunks = extract_chunks(paper)
    assert len(chunks) == 2
    assert [c.metadata["page"] for c in chunks] == [1, 3]
    assert [c.metadata["chunk_index"] for c in chunks] == [0, 0]
    for chunk in chunks:
        assert chunk.metadata["source"] == "paper.pdf"
        assert (
            chunk.metadata["document_id"]
            == hashlib.sha256(paper.read_bytes()).hexdigest()
        )
        assert UUID(point_id(chunk)).version == 5
    assert point_id(chunks[0]) != point_id(chunks[1])


def test_repeat_relocation_and_changed_bytes(paper, tmp_path):
    first = extract_chunks(paper)
    relocated = tmp_path / "renamed.pdf"
    relocated.write_bytes(paper.read_bytes())
    assert [point_id(c) for c in first] == [
        point_id(c) for c in extract_chunks(relocated)
    ]
    paper.write_bytes(paper.read_bytes() + b"\n%changed\n")
    assert (
        first[0].metadata["document_id"]
        != extract_chunks(paper)[0].metadata["document_id"]
    )


def test_chunk_boundaries_and_overlap(monkeypatch, tmp_path):
    path = tmp_path / "fake.pdf"
    path.write_bytes(b"test")
    text = "".join(chr(0x4E00 + index) for index in range(2100))

    class Page:
        def get_text(self, mode):
            assert mode == "text"
            return text

    class PDF:
        needs_pass = False

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def __iter__(self):
            return iter([Page()])

    monkeypatch.setattr(documents.pymupdf, "open", lambda **kwargs: PDF())
    chunks = extract_chunks(path)
    assert [len(c.page_content) for c in chunks] == [1000, 1000, 500]
    assert chunks[0].page_content[-200:] == chunks[1].page_content[:200]
    assert [c.metadata["chunk_index"] for c in chunks] == [0, 1, 2]


@pytest.mark.parametrize("kind", ["missing", "corrupt", "blank", "unreadable"])
def test_pdf_failures(kind, tmp_path, monkeypatch):
    path = tmp_path / "bad.pdf"
    if kind == "corrupt":
        path.write_bytes(b"not a pdf")
    elif kind == "blank":
        with pymupdf.open() as pdf:
            pdf.new_page()
            pdf.save(path)
    elif kind == "unreadable":

        def denied(self):
            raise PermissionError("secret")

        monkeypatch.setattr(Path, "read_bytes", denied)
    with pytest.raises(PipelineError) as error:
        extract_chunks(path)
    assert "secret" not in str(error.value)
