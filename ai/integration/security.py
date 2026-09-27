"""Security, input validation, and privacy protection for CoverWise AI.

Defines:
- Safe PDF upload validation (size limits, extension, magic bytes, path traversal defense).
- Sensitive PHI and token redaction (SSN, MRN, email, phone, auth tokens).
- Logging filter preventing sensitive health/auth information leakage.
"""

from io import BytesIO
import logging
from pathlib import Path
import re
from typing import BinaryIO

import fitz  # PyMuPDF


class UnsafeUploadError(ValueError):
    """Raised when an uploaded document fails security validation."""


class InvalidPDFError(ValueError):
    """Raised when a document is not a valid, decodable PDF."""


# Maximum allowed PDF file size (25 MB)
MAX_PDF_SIZE_BYTES = 25 * 1024 * 1024
PDF_MAGIC_BYTES = b"%PDF-"

# Regular expressions for scrubbing sensitive patient/auth details
SSN_PATTERN = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
CARD_PATTERN = re.compile(r"\b\d{4}[ -]?\d{4}[ -]?\d{4}[ -]?\d{4}\b")
PHONE_PATTERN = re.compile(r"\b(?:\+?1[-.]?)?\(?[0-9]{3}\)?[-. ]?[0-9]{3}[-. ]?[0-9]{4}\b")
EMAIL_PATTERN = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b")
BEARER_PATTERN = re.compile(r"Bearer\s+[a-zA-Z0-9._-]+", re.IGNORECASE)
MEMBER_ID_PATTERN = re.compile(r"\b(?:MRN|Member\s*ID)[:#\s]*[A-Za-z0-9-]{6,}\b", re.IGNORECASE)


def validate_pdf_file(
    file_input: str | Path | bytes | BinaryIO,
    max_size_bytes: int = MAX_PDF_SIZE_BYTES,
    allowed_dir: Path | None = None,
) -> Path:
    """Validate a PDF document for size, path traversal, magic bytes, and structure.

    Args:
        file_input: File path, bytes, or open file stream.
        max_size_bytes: Maximum permitted size in bytes.
        allowed_dir: Optional directory to constrain path resolution.

    Returns:
        Validated Path instance.

    Raises:
        UnsafeUploadError: On path traversal, oversized file, or security violation.
        InvalidPDFError: On missing file, corrupt content, or invalid magic bytes.
    """
    if isinstance(file_input, (str, Path)):
        raw_path = Path(file_input)
        str_path = str(raw_path)

        # 1. Path traversal defense
        if ".." in str_path or "\x00" in str_path:
            raise UnsafeUploadError(f"Path traversal or invalid characters detected in path: '{str_path}'")

        resolved = raw_path.resolve()
        if allowed_dir:
            allowed_res = allowed_dir.resolve()
            if not resolved.is_relative_to(allowed_res):
                raise UnsafeUploadError(f"Path '{resolved}' is outside allowed directory '{allowed_res}'")

        if not resolved.exists():
            raise InvalidPDFError(f"PDF file does not exist: {resolved}")
        if not resolved.is_file():
            raise InvalidPDFError(f"Path is not a regular file: {resolved}")

        # Check extension
        if resolved.suffix.lower() != ".pdf":
            raise InvalidPDFError(f"File must have a .pdf extension, got: '{resolved.suffix}'")

        # 2. Size check
        size = resolved.stat().st_size
        if size == 0:
            raise InvalidPDFError(f"PDF file is completely empty (0 bytes): {resolved}")
        if size > max_size_bytes:
            raise UnsafeUploadError(
                f"File size {size} bytes exceeds maximum permitted size of {max_size_bytes} bytes."
            )

        # 3. Magic bytes signature check
        with open(resolved, "rb") as f:
            header = f.read(5)
            if not header.startswith(PDF_MAGIC_BYTES):
                raise InvalidPDFError(
                    f"Invalid PDF file header signature. Expected '{PDF_MAGIC_BYTES.decode()}', got '{header[:5]!r}'"
                )

        # 4. PyMuPDF integrity verification
        try:
            doc = fitz.open(resolved)
            if doc.is_encrypted:
                doc.close()
                raise InvalidPDFError("Encrypted or password-protected PDFs are not supported.")
            if len(doc) == 0:
                doc.close()
                raise InvalidPDFError("PDF document contains 0 pages.")
            doc.close()
        except Exception as exc:
            if isinstance(exc, (InvalidPDFError, UnsafeUploadError)):
                raise
            raise InvalidPDFError(f"Malformed or corrupt PDF structure: {exc}") from exc

        return resolved

    elif isinstance(file_input, bytes):
        if len(file_input) == 0:
            raise InvalidPDFError("PDF byte stream is empty (0 bytes).")
        if len(file_input) > max_size_bytes:
            raise UnsafeUploadError(
                f"Byte stream size {len(file_input)} bytes exceeds maximum {max_size_bytes} bytes."
            )
        if not file_input.startswith(PDF_MAGIC_BYTES):
            raise InvalidPDFError("Invalid PDF header signature in byte stream.")
        try:
            doc = fitz.open(stream=file_input, filetype="pdf")
            if doc.is_encrypted or len(doc) == 0:
                doc.close()
                raise InvalidPDFError("PDF is encrypted or has 0 pages.")
            doc.close()
        except Exception as exc:
            raise InvalidPDFError(f"Malformed PDF byte stream: {exc}") from exc
        # Write to safe temporary location if path required
        import tempfile
        tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
        tmp.write(file_input)
        tmp.close()
        return Path(tmp.name)

    else:
        raise TypeError(f"Unsupported file_input type: {type(file_input)}")


def mask_sensitive_phi(text: str) -> str:
    """Mask sensitive patient health information, identifiers, and credentials."""
    if not text:
        return text

    masked = SSN_PATTERN.sub("[REDACTED_SSN]", text)
    masked = CARD_PATTERN.sub("[REDACTED_CARD]", masked)
    masked = PHONE_PATTERN.sub("[REDACTED_PHONE]", masked)
    masked = EMAIL_PATTERN.sub("[REDACTED_EMAIL]", masked)
    masked = BEARER_PATTERN.sub("Bearer [REDACTED_TOKEN]", masked)
    masked = MEMBER_ID_PATTERN.sub("Member ID: [REDACTED_ID]", masked)
    return masked


class SensitiveDataFilter(logging.Filter):
    """Logging filter that scrubs sensitive PHI and credentials before output."""

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = mask_sensitive_phi(record.msg)
        if record.args:
            if isinstance(record.args, tuple):
                record.args = tuple(
                    mask_sensitive_phi(a) if isinstance(a, str) else a
                    for a in record.args
                )
            elif isinstance(record.args, dict):
                record.args = {
                    k: mask_sensitive_phi(v) if isinstance(v, str) else v
                    for k, v in record.args.items()
                }
        return True


def install_sensitive_log_filter() -> None:
    """Attach SensitiveDataFilter to all active handlers in the CoverWise logging tree."""
    target_logger = logging.getLogger("coverwise_ai")
    fil = SensitiveDataFilter()
    target_logger.addFilter(fil)
    for h in target_logger.handlers:
        h.addFilter(fil)
