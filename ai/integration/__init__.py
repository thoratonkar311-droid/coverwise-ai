"""CoverWise AI Integration Package.

Provides production-ready Pydantic v2 interfaces and orchestration service
for Member 2's FastAPI backend.
"""

from ai.integration.models import (
    AIHealthCheckResponse,
    ClauseRetrieveRequest,
    ClauseRetrieveResponse,
    PolicyExtractRequest,
    PolicyExtractResponse,
    PolicyIndexRequest,
    PolicyIndexResponse,
    PolicyQuestionRequest,
    PolicyQuestionResponse,
    PolicyDeleteRequest,
    PolicyDeleteResponse,
    RetrievedClauseItem,
)
from ai.integration.security import (
    InvalidPDFError,
    SensitiveDataFilter,
    UnsafeUploadError,
    install_sensitive_log_filter,
    mask_sensitive_phi,
    validate_pdf_file,
)
from ai.integration.service import AIService, get_ai_service

__all__ = [
    "AIService",
    "get_ai_service",
    "PolicyExtractRequest",
    "PolicyExtractResponse",
    "PolicyIndexRequest",
    "PolicyIndexResponse",
    "PolicyDeleteRequest",
    "PolicyDeleteResponse",
    "ClauseRetrieveRequest",
    "ClauseRetrieveResponse",
    "RetrievedClauseItem",
    "PolicyQuestionRequest",
    "PolicyQuestionResponse",
    "AIHealthCheckResponse",
    "validate_pdf_file",
    "mask_sensitive_phi",
    "SensitiveDataFilter",
    "install_sensitive_log_filter",
    "UnsafeUploadError",
    "InvalidPDFError",
]
