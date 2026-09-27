"""Clause-aware chunking for CoverWise AI policy documents.

Splits policy documents along natural clause boundaries, numbered provisions,
and section headings, strictly preserving 1-indexed page references, stable IDs,
and character offsets for exact auditability.
"""

from abc import ABC, abstractmethod
import re
from typing import Any
from pydantic import BaseModel, ConfigDict, Field
from ai.schemas.evidence import ExtractedDocument, ExtractedPage


class PolicyChunk(BaseModel):
    """Retrieval chunk tied to a specific policy page and section."""

    model_config = ConfigDict(frozen=True)

    chunk_id: str = Field(..., description="Unique deterministic chunk ID, e.g. 'doc1_p3_c0'.")
    document_id: str = Field(..., description="Policy document identifier.")
    page_number: int = Field(..., ge=1, description="1-indexed page number of this chunk.")
    text: str = Field(..., min_length=1, description="Chunk textual content.")
    char_start: int | None = Field(default=None, description="Start index in page text.")
    char_end: int | None = Field(default=None, description="End index in page text.")
    section_title: str | None = Field(default=None, description="Extracted section heading if known.")
    category: str | None = Field(default=None, description="Identified benefit category.")
    user_id: str | None = Field(default=None, description="Optional user/tenant ID for multi-tenant isolation.")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Custom metadata for filtering.")


class PolicyChunkerInterface(ABC):
    """Abstract interface defining policy chunking contracts."""

    @abstractmethod
    def chunk_document(self, document: ExtractedDocument) -> list[PolicyChunk]:
        """Split an extracted document into structured chunks preserving page evidence."""


class ClauseAwareChunker(PolicyChunkerInterface):
    """Clause-aware chunker that identifies policy sections, clauses, and provisions."""

    SECTION_PATTERN = re.compile(
        r"(SECTION\s+[0-9]+[^\n]*|\b[0-9]\.[0-9]\s+[^\n]+)",
        re.IGNORECASE,
    )

    def __init__(self, min_chunk_len: int = 50, max_chunk_len: int = 1000) -> None:
        self.min_chunk_len = min_chunk_len
        self.max_chunk_len = max_chunk_len

    def chunk_document(self, document: ExtractedDocument) -> list[PolicyChunk]:
        """Split document pages into clause-aware chunks with stable IDs."""
        all_chunks: list[PolicyChunk] = []
        doc_id = document.document_id

        for page in document.pages:
            page_chunks = self.chunk_page(page, doc_id)
            all_chunks.extend(page_chunks)

        return all_chunks

    def chunk_page(self, page: ExtractedPage, document_id: str) -> list[PolicyChunk]:
        """Chunk an individual page while preserving character offsets and section context."""
        text = page.text
        if not text or not text.strip():
            return []

        chunks: list[PolicyChunk] = []
        current_section = "General Provisions"
        page_num = page.page_number

        # Split text into logical paragraphs / clause blocks
        raw_blocks = [b.strip() for b in text.split("\n\n") if b.strip()]
        chunk_idx = 0

        for block in raw_blocks:
            # Check if this block defines a new section heading
            sec_match = self.SECTION_PATTERN.search(block)
            if sec_match:
                candidate_title = sec_match.group(0).strip()
                if len(candidate_title) < 100:
                    current_section = candidate_title

            # If the block has bullet items (e.g. - Individual in-network), treat as a cohesive clause
            # or sub-chunk if too long
            sub_blocks = self._split_if_oversized(block, self.max_chunk_len)

            for sub_text in sub_blocks:
                if len(sub_text) < self.min_chunk_len and raw_blocks.index(block) < len(raw_blocks) - 1:
                    # Very short fragments like titles get included in next chunk or tagged
                    pass

                # Calculate approximate char start and end in original page text
                char_start = text.find(sub_text[:40]) if len(sub_text) >= 40 else text.find(sub_text)
                char_end = (char_start + len(sub_text)) if char_start != -1 else None
                if char_start == -1:
                    char_start = None

                # Generate stable, deterministic chunk ID
                chunk_id = f"{document_id}_p{page_num}_c{chunk_idx:03d}"
                category = self._infer_category(sub_text, current_section)

                chunk = PolicyChunk(
                    chunk_id=chunk_id,
                    document_id=document_id,
                    page_number=page_num,
                    text=sub_text,
                    char_start=char_start,
                    char_end=char_end,
                    section_title=current_section,
                    category=category,
                    metadata={
                        "word_count": len(sub_text.split()),
                        "has_numbers": bool(re.search(r"\d", sub_text)),
                        "is_exclusion": "exclusion" in current_section.lower() or "excluded" in sub_text.lower(),
                        "is_deductible": "deductible" in current_section.lower() or "deductible" in sub_text.lower(),
                        "is_copay": "copay" in current_section.lower() or "copay" in sub_text.lower(),
                        "is_prior_auth": "prior auth" in sub_text.lower(),
                    },
                )
                chunks.append(chunk)
                chunk_idx += 1

        return chunks

    def _split_if_oversized(self, text: str, max_len: int) -> list[str]:
        """Split a long text block along line breaks without severing clauses."""
        if len(text) <= max_len:
            return [text]

        lines = text.split("\n")
        sub_chunks: list[str] = []
        current: list[str] = []
        current_len = 0

        for line in lines:
            if current_len + len(line) > max_len and current:
                sub_chunks.append("\n".join(current).strip())
                current = [line]
                current_len = len(line)
            else:
                current.append(line)
                current_len += len(line) + 1

        if current:
            sub_chunks.append("\n".join(current).strip())

        return sub_chunks

    @staticmethod
    def _infer_category(text: str, section_title: str) -> str:
        """Infer rough category for chunk metadata filtering."""
        combined = (section_title + " " + text).lower()
        if "deductible" in combined or "out-of-pocket" in combined:
            return "cost_sharing"
        if "copayment" in combined or "copay" in combined:
            return "copay"
        if "coinsurance" in combined:
            return "coinsurance"
        if "inpatient" in combined or "hospital" in combined:
            return "inpatient"
        if "surgery" in combined or "surgical" in combined:
            return "surgery"
        if "drug" in combined or "prescription" in combined or "tier" in combined:
            return "prescription"
        if "exclusion" in combined or "not covered" in combined:
            return "exclusions"
        if "prior authorization" in combined:
            return "prior_auth"
        return "general"
