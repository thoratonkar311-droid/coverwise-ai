"""Tests for PyMuPDF PDF extractor.

Verifies page-level text extraction, 1-indexed page numbering preservation,
error handling, and evidence preservation.
"""

from pathlib import Path
import pytest

from ai.extraction.pdf_extractor import (
    CorruptPDFError,
    PDFExtractor,
    PDFNotFoundError,
)


def test_extract_sample_policy(sample_pdf_path):
    """Verify extraction of the 4-page synthetic policy fixture."""
    extractor = PDFExtractor(clean_text=True)
    doc = extractor.extract(sample_pdf_path)

    assert doc.filename == "sample_health_policy.pdf"
    assert doc.total_pages == 4
    assert len(doc.pages) == 4
    assert doc.document_id is not None
    assert len(doc.document_id) == 64  # SHA-256 length

    # Verify 1-indexed page numbers
    for idx, page in enumerate(doc.pages):
        expected_page_num = idx + 1
        assert page.page_number == expected_page_num
        assert page.char_count > 0
        assert page.word_count > 0

    # Verify specific policy sections per page
    assert "ANNUAL DEDUCTIBLES" in doc.pages[0].text
    assert "$1,500.00" in doc.pages[0].text

    assert "COPAYMENTS AND COINSURANCE" in doc.pages[1].text
    assert "Emergency Room" in doc.pages[1].text

    assert "SURGICAL SERVICES" in doc.pages[2].text
    assert "Prior authorization is strictly required" in doc.pages[2].text

    assert "EXCLUSIONS AND LIMITATIONS" in doc.pages[3].text
    assert "Cosmetic surgery" in doc.pages[3].text


def test_missing_pdf_raises_not_found(tmp_path):
    """Verify PDFNotFoundError when non-existent path is passed."""
    non_existent = tmp_path / "does_not_exist.pdf"
    extractor = PDFExtractor()
    with pytest.raises(PDFNotFoundError) as exc_info:
        extractor.extract(non_existent)
    assert "does_not_exist.pdf" in str(exc_info.value)


def test_corrupt_pdf_raises_corrupt_error(tmp_path):
    """Verify CorruptPDFError when file content is not a valid PDF."""
    corrupt_file = tmp_path / "corrupt.pdf"
    corrupt_file.write_text("THIS IS NOT A VALID PDF FILE FORMAT")

    extractor = PDFExtractor()
    with pytest.raises(CorruptPDFError):
        extractor.extract(corrupt_file)


def test_empty_page_handling(temp_pdf_factory):
    """Verify extraction handles blank/empty pages gracefully without crashing."""
    pages = [
        "First page with content.",
        "",  # Blank page
        "Third page with content.",
    ]
    pdf_path = temp_pdf_factory(pages, filename="with_blank_page.pdf")

    extractor = PDFExtractor()
    doc = extractor.extract(pdf_path)

    assert doc.total_pages == 3
    assert doc.pages[0].page_number == 1
    assert doc.pages[0].char_count > 0

    assert doc.pages[1].page_number == 2
    assert doc.pages[1].text == ""
    assert doc.pages[1].char_count == 0

    assert doc.pages[2].page_number == 3
    assert doc.pages[2].char_count > 0


def test_full_text_joins_with_delimiter(temp_pdf_factory):
    """Verify full text output joins pages with clear separation."""
    pages = ["Page one content", "Page two content"]
    pdf_path = temp_pdf_factory(pages, filename="multi.pdf")

    doc = PDFExtractor().extract(pdf_path)
    full = doc.get_full_text()
    assert "Page one content" in full
    assert "Page two content" in full
    assert "--- Page Break ---" in full
