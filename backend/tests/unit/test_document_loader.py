"""
Unit tests for app.document_processing.loader.DocumentLoader
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.document_processing.loader import (
    DocumentLoadError,
    DocumentLoader,
    UnsupportedDocumentTypeError,
)
from app.models.document import DocumentType

pytestmark = pytest.mark.unit


# ── load_text ──────────────────────────────────────────────────────────────────

class TestLoadText:
    def test_returns_text_and_metadata(self):
        loader = DocumentLoader()
        text, meta = loader.load_text("Some legal content here.", "doc.txt")
        assert text == "Some legal content here."
        assert meta.filename == "doc.txt"
        assert meta.document_type == DocumentType.TXT
        assert meta.file_size_bytes > 0

    def test_strips_surrounding_whitespace(self):
        loader = DocumentLoader()
        text, _ = loader.load_text("  Legal text.  ")
        assert text == "Legal text."

    def test_raises_on_empty_string(self):
        loader = DocumentLoader()
        with pytest.raises(DocumentLoadError):
            loader.load_text("")

    def test_raises_on_whitespace_only(self):
        loader = DocumentLoader()
        with pytest.raises(DocumentLoadError):
            loader.load_text("   \n  ")

    def test_document_ids_are_unique(self):
        loader = DocumentLoader()
        _, meta1 = loader.load_text("Text 1")
        _, meta2 = loader.load_text("Text 2")
        assert meta1.document_id != meta2.document_id


# ── load TXT files ─────────────────────────────────────────────────────────────

class TestLoadTxtFile:
    def test_loads_txt_successfully(self, tmp_path: Path, sample_legal_text: str):
        f = tmp_path / "case.txt"
        f.write_text(sample_legal_text, encoding="utf-8")
        loader = DocumentLoader()
        text, meta = loader.load(str(f))
        assert text == sample_legal_text.strip()
        assert meta.document_type == DocumentType.TXT
        assert meta.filename == "case.txt"

    def test_raises_on_empty_txt(self, tmp_path: Path):
        f = tmp_path / "empty.txt"
        f.write_text("", encoding="utf-8")
        loader = DocumentLoader()
        with pytest.raises(DocumentLoadError):
            loader.load(str(f))

    def test_source_path_is_absolute(self, tmp_path: Path, sample_legal_text: str):
        f = tmp_path / "case.txt"
        f.write_text(sample_legal_text)
        loader = DocumentLoader()
        _, meta = loader.load(str(f))
        assert Path(meta.source_path).is_absolute()


# ── unsupported types ──────────────────────────────────────────────────────────

class TestUnsupportedTypes:
    def test_raises_for_xlsx(self, tmp_path: Path):
        f = tmp_path / "data.xlsx"
        f.write_bytes(b"fake")
        with pytest.raises(UnsupportedDocumentTypeError):
            DocumentLoader().load(str(f))

    def test_raises_for_csv(self, tmp_path: Path):
        f = tmp_path / "data.csv"
        f.write_text("col1,col2\nval1,val2")
        with pytest.raises(UnsupportedDocumentTypeError):
            DocumentLoader().load(str(f))

    def test_error_lists_supported_types(self, tmp_path: Path):
        f = tmp_path / "report.html"
        f.write_text("<html></html>")
        with pytest.raises(UnsupportedDocumentTypeError) as exc_info:
            DocumentLoader().load(str(f))
        assert ".txt" in str(exc_info.value)


# ── PDF loading ────────────────────────────────────────────────────────────────

class TestLoadPdf:
    def test_loads_pdf_with_text(self, tmp_path: Path):
        f = tmp_path / "case.pdf"
        f.write_bytes(b"%PDF-1.4 fake")

        mock_page = MagicMock()
        mock_page.extract_text.return_value = "Extracted legal text from PDF."
        mock_pdf = MagicMock()
        mock_pdf.__enter__ = MagicMock(return_value=mock_pdf)
        mock_pdf.__exit__ = MagicMock(return_value=False)
        mock_pdf.pages = [mock_page]

        with patch("app.document_processing.loader.pdfplumber.open", return_value=mock_pdf):
            text, meta = DocumentLoader().load(str(f))

        assert "Extracted legal text" in text
        assert meta.document_type == DocumentType.PDF

    def test_raises_when_pdf_yields_no_text(self, tmp_path: Path):
        f = tmp_path / "empty.pdf"
        f.write_bytes(b"%PDF-1.4 fake")

        mock_page = MagicMock()
        mock_page.extract_text.return_value = ""
        mock_pdf = MagicMock()
        mock_pdf.__enter__ = MagicMock(return_value=mock_pdf)
        mock_pdf.__exit__ = MagicMock(return_value=False)
        mock_pdf.pages = [mock_page]

        with patch("app.document_processing.loader.pdfplumber.open", return_value=mock_pdf):
            with pytest.raises(DocumentLoadError):
                DocumentLoader().load(str(f))
