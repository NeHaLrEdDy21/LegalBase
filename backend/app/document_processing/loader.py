"""
Document loader — reads PDF, DOCX, and plain-text files and returns raw text.
All I/O errors are surfaced as explicit, typed exceptions.
"""
import logging
from pathlib import Path

import pdfplumber
from docx import Document as DocxDocument

from app.models.document import DocumentMetadata, DocumentType

logger = logging.getLogger(__name__)


class UnsupportedDocumentTypeError(ValueError):
    """Raised when a file extension is not supported."""


class DocumentLoadError(IOError):
    """Raised when a document cannot be read."""


class DocumentLoader:
    """Loads a file from disk and extracts its text content."""

    _SUPPORTED: dict[str, DocumentType] = {
        ".pdf": DocumentType.PDF,
        ".docx": DocumentType.DOCX,
        ".txt": DocumentType.TXT,
    }

    def load(self, file_path: str | Path) -> tuple[str, DocumentMetadata]:
        """
        Load *file_path* and return ``(raw_text, metadata)``.

        Raises
        ------
        UnsupportedDocumentTypeError
            If the file extension is not in ``.pdf | .docx | .txt``.
        DocumentLoadError
            If the file cannot be read or parsed.
        """
        path = Path(file_path)
        ext = path.suffix.lower()

        if ext not in self._SUPPORTED:
            raise UnsupportedDocumentTypeError(
                f"Unsupported file type '{ext}'. "
                f"Supported types: {list(self._SUPPORTED)}"
            )

        doc_type = self._SUPPORTED[ext]

        try:
            if doc_type == DocumentType.PDF:
                text = self._load_pdf(path)
            elif doc_type == DocumentType.DOCX:
                text = self._load_docx(path)
            else:
                text = self._load_txt(path)
        except (UnsupportedDocumentTypeError, DocumentLoadError):
            raise
        except Exception as exc:
            raise DocumentLoadError(
                f"Failed to load '{path}': {exc}"
            ) from exc

        metadata = DocumentMetadata(
            filename=path.name,
            document_type=doc_type,
            file_size_bytes=path.stat().st_size,
            source_path=str(path.resolve()),
        )
        logger.info(
            "Loaded document '%s' (%s bytes, type=%s)",
            path.name,
            metadata.file_size_bytes,
            doc_type,
        )
        return text, metadata

    # ── private helpers ────────────────────────────────────────────────────────

    @staticmethod
    def _load_pdf(path: Path) -> str:
        pages: list[str] = []
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text() or ""
                pages.append(page_text)
        text = "\n".join(pages).strip()
        if not text:
            raise DocumentLoadError(f"PDF '{path}' yielded no extractable text.")
        return text

    @staticmethod
    def _load_docx(path: Path) -> str:
        doc = DocxDocument(str(path))
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        text = "\n".join(paragraphs).strip()
        if not text:
            raise DocumentLoadError(f"DOCX '{path}' contained no text paragraphs.")
        return text

    @staticmethod
    def _load_txt(path: Path) -> str:
        text = path.read_text(encoding="utf-8", errors="replace").strip()
        if not text:
            raise DocumentLoadError(f"TXT file '{path}' is empty.")
        return text

    def load_text(
        self,
        text: str,
        filename: str = "manual_input.txt",
    ) -> tuple[str, DocumentMetadata]:
        """
        Accept raw text directly (no file I/O).
        Used by the REST endpoint that receives text in the request body.
        """
        if not text or not text.strip():
            raise DocumentLoadError("Provided text is empty.")

        metadata = DocumentMetadata(
            filename=filename,
            document_type=DocumentType.TXT,
            file_size_bytes=len(text.encode()),
        )
        return text.strip(), metadata
