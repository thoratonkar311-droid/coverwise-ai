"""Optional Optical Character Recognition (OCR) module for CoverWise AI.

Kept strictly optional to avoid heavy C++/PaddlePaddle dependencies unless
explicitly required and enabled by environment configuration.
"""

from abc import ABC, abstractmethod
import importlib.util
import logging
from typing import Any

logger = logging.getLogger("coverwise_ai.extraction.ocr")


class OCRError(Exception):
    """Base exception for OCR processing."""


class OCREngineNotInstalledError(OCRError):
    """Raised when an OCR operation is requested but the engine is not installed."""


class OCRExtractorInterface(ABC):
    """Abstract interface defining the contract for OCR engine implementations."""

    @abstractmethod
    def is_available(self) -> bool:
        """Check whether the underlying OCR engine dependencies are installed."""

    @abstractmethod
    def extract_text_from_image(self, image_bytes: bytes) -> str:
        """Extract plain text from image bytes.

        Args:
            image_bytes: Raw bytes of a page image (PNG, JPEG).

        Returns:
            Extracted text string.
        """


class OptionalPaddleOCRExtractor(OCRExtractorInterface):
    """PaddleOCR extractor wrapper with graceful degradation if uninstalled."""

    def __init__(self, lang: str = "en") -> None:
        self.lang = lang
        self._engine: Any = None
        self._available = importlib.util.find_spec("paddleocr") is not None

    def is_available(self) -> bool:
        """Return True if PaddleOCR is importable."""
        return self._available

    def _load_engine(self) -> Any:
        """Lazy load PaddleOCR engine if available."""
        if not self._available:
            raise OCREngineNotInstalledError(
                "PaddleOCR is not installed in the current Python environment. "
                "To enable OCR fallback, install 'paddleocr' or use PyMuPDF native text extraction."
            )
        if self._engine is None:
            logger.info("Initializing PaddleOCR engine with lang=%s", self.lang)
            from paddleocr import PaddleOCR  # type: ignore

            self._engine = PaddleOCR(use_angle_cls=True, lang=self.lang)
        return self._engine

    def extract_text_from_image(self, image_bytes: bytes) -> str:
        """Extract text from raw image bytes using PaddleOCR.

        Args:
            image_bytes: Raw bytes of the rendered page.

        Returns:
            Extracted text string.
        """
        engine = self._load_engine()
        try:
            results = engine.ocr(image_bytes, cls=True)
            extracted_lines: list[str] = []
            if results and results[0]:
                for line in results[0]:
                    # line format: [coordinates, (text, confidence)]
                    text = line[1][0]
                    extracted_lines.append(text)
            return "\n".join(extracted_lines)
        except Exception as exc:
            logger.error("OCR extraction failed: %s", exc)
            raise OCRError(f"Failed to perform OCR on image: {exc}") from exc
