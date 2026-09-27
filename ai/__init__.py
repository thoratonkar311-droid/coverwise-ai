"""CoverWise AI - AI/ML Module.

Policy-to-Patient Insurance Coverage & Treatment Cost Intelligence.
"""

from ai.extraction.policy_extractor import extract_policy, PolicyExtractor
from ai.extraction.pdf_extractor import PDFExtractor
from ai.retrieval.retriever import (
    index_policy,
    retrieve_clauses,
    answer_policy_question,
)
from ai.integration.service import AIService, get_ai_service

__version__ = "0.3.0"

__all__ = [
    "extract_policy",
    "PolicyExtractor",
    "PDFExtractor",
    "index_policy",
    "retrieve_clauses",
    "answer_policy_question",
    "AIService",
    "get_ai_service",
]
