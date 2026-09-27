"""Evidence and document extraction schemas for CoverWise AI.

Ensures strict traceability, source citations, and page-level evidence preservation.
"""

from typing import Any
from pydantic import BaseModel, ConfigDict, Field


class BoundingBox(BaseModel):
    """Coordinates of text or element within a document page."""

    model_config = ConfigDict(frozen=True)

    x0: float = Field(..., description="Left coordinate")
    y0: float = Field(..., description="Top coordinate")
    x1: float = Field(..., description="Right coordinate")
    y1: float = Field(..., description="Bottom coordinate")


class EvidenceSpan(BaseModel):
    """Verbatim text snippet tied to a specific page and clause for auditability."""

    model_config = ConfigDict(frozen=True)

    text: str = Field(..., min_length=1, description="Verbatim text quote from policy.")
    page_number: int = Field(..., ge=1, description="1-indexed document page number.")
    char_start: int | None = Field(
        default=None,
        ge=0,
        description="Character start index in the page text.",
    )
    char_end: int | None = Field(
        default=None,
        ge=0,
        description="Character end index in the page text.",
    )
    clause_reference: str | None = Field(
        default=None,
        description="Section or clause identifier (e.g. 'Section 3.1.2').",
    )
    confidence_score: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Extraction confidence score if available.",
    )


class ExtractedPage(BaseModel):
    """Structured representation of a single extracted PDF page."""

    model_config = ConfigDict(validate_assignment=True)

    page_number: int = Field(..., ge=1, description="1-indexed page number.")
    text: str = Field(default="", description="Extracted plain text for this page.")
    char_count: int = Field(default=0, ge=0, description="Total characters extracted.")
    word_count: int = Field(default=0, ge=0, description="Total words extracted.")
    has_images: bool = Field(default=False, description="Whether the page contains images.")
    is_ocr: bool = Field(default=False, description="Whether OCR was used for this page.")
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Arbitrary page-level metadata (e.g., orientation, font info).",
    )


class ExtractedDocument(BaseModel):
    """Structured representation of an entire extracted policy document."""

    model_config = ConfigDict(validate_assignment=True)

    document_id: str = Field(..., description="Unique document identifier (UUID or SHA-256).")
    filename: str = Field(..., description="Original filename of the policy document.")
    total_pages: int = Field(..., ge=0, description="Total page count of the document.")
    pages: list[ExtractedPage] = Field(
        default_factory=list,
        description="List of extracted pages preserved in sequence.",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Document-level metadata (author, title, creation_date, etc.).",
    )
    file_size_bytes: int | None = Field(
        default=None,
        ge=0,
        description="Size of the raw PDF file in bytes.",
    )

    def get_full_text(self) -> str:
        """Combine text across all pages with standard page delimiter."""
        return "\n\n--- Page Break ---\n\n".join(page.text for page in self.pages)

    def get_page(self, page_number: int) -> ExtractedPage | None:
        """Retrieve a specific page by its 1-indexed page number."""
        for page in self.pages:
            if page.page_number == page_number:
                return page
        return None


class Citation(BaseModel):
    """External citation reference for UI display and backend auditing."""

    model_config = ConfigDict(frozen=True)

    document_name: str | None = Field(default=None, description="Name of the cited document.")
    page_number: int = Field(..., ge=1, description="1-indexed page number.")
    clause_title: str | None = Field(default=None, description="Title of the cited clause.")
    clause_reference: str | None = Field(default=None, description="Clause/section number.")
    verbatim_text: str = Field(..., description="Verbatim policy text cited as evidence.")
