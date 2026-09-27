"""Basic working PDF text extractor for CoverWise AI.

Uses PyMuPDF (fitz) to extract text while strictly preserving 1-indexed page
numbers, character counts, and structural evidence for auditability.
"""

import hashlib
import logging
from pathlib import Path
from typing import Any

try:
    import pymupdf as fitz
except ImportError:
    import fitz  # type: ignore

from ai.schemas.evidence import ExtractedDocument, ExtractedPage

logger = logging.getLogger("coverwise_ai.extraction.pdf")


class ExtractionError(Exception):
    """Base exception for PDF extraction failures."""


class PDFNotFoundError(ExtractionError):
    """Raised when the specified PDF file cannot be found."""


class CorruptPDFError(ExtractionError):
    """Raised when the PDF file is corrupted or cannot be parsed."""


class PDFExtractor:
    """Extracts text content from PDF policy documents while preserving page structure."""

    def __init__(self, clean_text: bool = True) -> None:
        """Initialize PDFExtractor.

        Args:
            clean_text: Whether to normalize whitespace and non-printable characters.
        """
        self.clean_text = clean_text

    def extract(self, file_path: str | Path) -> ExtractedDocument:
        """Extract all pages and text from a PDF document.

        Args:
            file_path: Path to the target PDF file.

        Returns:
            ExtractedDocument containing sequentially preserved ExtractedPage objects.

        Raises:
            PDFNotFoundError: If the file does not exist on disk.
            CorruptPDFError: If PyMuPDF fails to open or parse the file.
            ExtractionError: If any other unexpected error occurs during extraction.
        """
        path = Path(file_path).resolve()
        if not path.is_file():
            logger.error("Target PDF file not found: %s", path)
            raise PDFNotFoundError(f"Policy PDF not found at path: {path}")

        logger.info("Opening PDF for text extraction: %s", path.name)

        try:
            doc = fitz.open(str(path))
        except Exception as exc:
            logger.error("Failed to open PDF document %s: %s", path.name, exc)
            raise CorruptPDFError(f"Unable to parse PDF '{path.name}': {exc}") from exc

        try:
            # Generate deterministic document ID from file content hash
            hasher = hashlib.sha256()
            with open(path, "rb") as f:
                while chunk := f.read(65536):
                    hasher.update(chunk)
            document_id = hasher.hexdigest()

            file_size_bytes = path.stat().st_size
            total_pages = len(doc)
            logger.info("Extracting %d pages from %s", total_pages, path.name)

            extracted_pages: list[ExtractedPage] = []
            doc_metadata: dict[str, Any] = {
                "title": doc.metadata.get("title") or None,
                "author": doc.metadata.get("author") or None,
                "subject": doc.metadata.get("subject") or None,
                "creator": doc.metadata.get("creator") or None,
                "producer": doc.metadata.get("producer") or None,
                "format": doc.metadata.get("format") or "PDF",
            }

            for page_index in range(total_pages):
                # Strict 1-indexed page numbering preserved
                page_number = page_index + 1
                page = doc.load_page(page_index)

                raw_text = page.get_text("text")
                processed_text = self._normalize_text(raw_text) if self.clean_text else raw_text

                # Check if page contains embedded images (useful signal for OCR necessity)
                image_list = page.get_images(full=True)
                has_images = len(image_list) > 0

                words = processed_text.split()
                extracted_page = ExtractedPage(
                    page_number=page_number,
                    text=processed_text,
                    char_count=len(processed_text),
                    word_count=len(words),
                    has_images=has_images,
                    is_ocr=False,
                    metadata={
                        "page_rect": [page.rect.x0, page.rect.y0, page.rect.x1, page.rect.y1],
                        "rotation": page.rotation,
                    },
                )
                extracted_pages.append(extracted_page)

                if not processed_text.strip():
                    logger.warning(
                        "Page %d of %s has no extractable text (image-only or blank).",
                        page_number,
                        path.name,
                    )
                else:
                    logger.debug(
                        "Page %d extracted: %d words, %d characters.",
                        page_number,
                        extracted_page.word_count,
                        extracted_page.char_count,
                    )

            logger.info("Successfully extracted %d pages from %s", len(extracted_pages), path.name)

            return ExtractedDocument(
                document_id=document_id,
                filename=path.name,
                total_pages=total_pages,
                pages=extracted_pages,
                metadata=doc_metadata,
                file_size_bytes=file_size_bytes,
            )

        except Exception as exc:
            if not isinstance(exc, ExtractionError):
                logger.exception("Unexpected error during PDF extraction: %s", exc)
                raise ExtractionError(f"Extraction failed for '{path.name}': {exc}") from exc
            raise
        finally:
            doc.close()

    @staticmethod
    def _normalize_text(text: str) -> str:
        """Clean and normalize extracted text while preserving logical paragraph breaks."""
        if not text:
            return ""

        # Replace carriage returns and excessive null / replacement chars
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        text = text.replace("\x00", "")

        # Strip trailing whitespaces per line while preserving structure
        lines = [line.strip() for line in text.split("\n")]

        # Collapse 3+ consecutive blank lines into 2
        cleaned_lines: list[str] = []
        blank_counter = 0
        for line in lines:
            if not line:
                blank_counter += 1
                if blank_counter <= 2:
                    cleaned_lines.append("")
            else:
                blank_counter = 0
                cleaned_lines.append(line)

        return "\n".join(cleaned_lines).strip()
