"""Extraction module for CoverWise AI.

Provides PDF extraction via PyMuPDF, optional OCR fallback interfaces,
and structured policy extraction (extract_policy) for Member 2.
"""

from ai.extraction.ocr_extractor import (
    OCREngineNotInstalledError,
    OCRError,
    OCRExtractorInterface,
    OptionalPaddleOCRExtractor,
)
from ai.extraction.pdf_extractor import (
    CorruptPDFError,
    ExtractionError,
    PDFExtractor,
    PDFNotFoundError,
)
from ai.extraction.policy_extractor import (
    PolicyExtractor,
    extract_policy,
)

__all__ = [
    "CorruptPDFError",
    "ExtractionError",
    "OCREngineNotInstalledError",
    "OCRError",
    "OCRExtractorInterface",
    "OptionalPaddleOCRExtractor",
    "PDFExtractor",
    "PDFNotFoundError",
    "PolicyExtractor",
    "extract_policy",
]
