from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class EvidenceReferenceBase(BaseModel):
    """Base fields representing direct citations from policy documentation."""

    document_source: str = Field(..., max_length=255, description="Source document filename or identifier")
    user_id: Optional[str] = Field(None, max_length=100, description="User identifier")
    page: Optional[int] = Field(None, ge=1, description="Page number of citation")
    clause_section: Optional[str] = Field(None, max_length=255, description="Policy section or clause heading")
    extracted_text: Optional[str] = Field(None, description="Exact text verbatim extracted from the policy")
    interpretation: Optional[str] = Field(None, description="Explanation of how clause impacts coverage")
    confidence: Optional[float] = Field(
        None, ge=0.0, le=1.0, description="Confidence score from extraction model (0.0 - 1.0)"
    )
    source_type: Optional[str] = Field(
        default="contractual_rule",
        description="Source classification: contractual_rule, example, estimate, explanation, exclusion, definition",
    )


class EvidenceReferenceCreate(EvidenceReferenceBase):
    """Schema for creating a new evidence reference."""

    policy_id: int = Field(..., description="ID of associated policy")
    rule_id: Optional[int] = Field(None, description="Associated coverage rule ID if applicable")
    analysis_id: Optional[int] = Field(None, description="Associated policy analysis ID if applicable")


class EvidenceReferenceResponse(EvidenceReferenceBase):
    """API response schema for evidence references."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    policy_id: int
    rule_id: Optional[int] = None
    analysis_id: Optional[int] = None
    created_at: datetime
