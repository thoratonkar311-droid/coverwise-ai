"""Pydantic schemas for request and response validation."""

from app.schemas.ai_contract import (
    CoverageAnalysisInput,
    DocumentExtractionInput,
    EvidenceItem,
    EvidenceQueryInput,
    EvidenceRetrievalOutput,
    ExtractedPolicyInfo,
    StructuredAIAnalysisResult,
    StructuredPolicyRules,
)
from app.schemas.coverage_rule import (
    CoverageRuleBase,
    CoverageRuleCreate,
    CoverageRuleResponse,
)
from app.schemas.dashboard import (
    DashboardResponse,
    DashboardStats,
)
from app.schemas.errors import ErrorDetail, ErrorResponse
from app.schemas.evidence_reference import (
    EvidenceReferenceBase,
    EvidenceReferenceCreate,
    EvidenceReferenceResponse,
)
from app.schemas.health import HealthResponse
from app.schemas.policy import (
    PolicyBase,
    PolicyCreate,
    PolicyResponse,
    PolicySummaryResponse,
    PolicyUpdate,
    PolicyUploadResponse,
)
from app.schemas.policy_analysis import (
    AnalysisCreate,
    AnalysisDetailResponse,
    AnalysisRequest,
    AnalysisResponse,
    CoverageResult,
)
from app.schemas.simulation import (
    SimulationRequest,
    SimulationResponse,
)
from app.schemas.treatment import (
    TreatmentBase,
    TreatmentCreate,
    TreatmentResponse,
)

__all__ = [
    # Health & Error
    "HealthResponse",
    "ErrorResponse",
    "ErrorDetail",
    # Policy
    "PolicyBase",
    "PolicyCreate",
    "PolicyUpdate",
    "PolicyResponse",
    "PolicySummaryResponse",
    "PolicyUploadResponse",
    # Coverage Rule
    "CoverageRuleBase",
    "CoverageRuleCreate",
    "CoverageRuleResponse",
    # Treatment
    "TreatmentBase",
    "TreatmentCreate",
    "TreatmentResponse",
    # Simulation
    "SimulationRequest",
    "SimulationResponse",
    # Evidence Reference
    "EvidenceReferenceBase",
    "EvidenceReferenceCreate",
    "EvidenceReferenceResponse",
    # Analysis
    "AnalysisRequest",
    "AnalysisCreate",
    "AnalysisResponse",
    "AnalysisDetailResponse",
    "CoverageResult",
    # Dashboard
    "DashboardStats",
    "DashboardResponse",
    # AI Contract & Structured Results
    "CoverageAnalysisInput",
    "DocumentExtractionInput",
    "EvidenceItem",
    "EvidenceQueryInput",
    "EvidenceRetrievalOutput",
    "ExtractedPolicyInfo",
    "StructuredAIAnalysisResult",
    "StructuredPolicyRules",
]
