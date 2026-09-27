from datetime import datetime
from typing import Any, List, Optional
from pydantic import BaseModel, ConfigDict, Field

from app.schemas.evidence_reference import EvidenceReferenceResponse


class CoverageRuleBase(BaseModel):
    """Base fields for structured coverage rules and policy restrictions."""

    coverage_status: str = Field(
        default="covered",
        max_length=50,
        description="Coverage determination: covered, not_covered, partially_covered, conditional",
    )
    deductible: Optional[float] = Field(None, ge=0.0, description="Deductible required before coverage kicks in")
    copay: Optional[float] = Field(None, ge=0.0, description="Fixed co-payment amount")
    copay_percentage: Optional[float] = Field(
        None, ge=0.0, le=100.0, description="Co-payment percentage payable by patient"
    )
    coverage_limit: Optional[float] = Field(None, ge=0.0, description="Sum insured or maximum cap on procedure")
    exclusions: Optional[Any] = Field(None, description="Excluded treatments, conditions, or clauses")
    waiting_period: Optional[str] = Field(None, max_length=100, description="Required waiting period before coverage")
    room_category: Optional[str] = Field(
        None, max_length=100, description="Eligible hospital room category or rent limitation"
    )
    source_reference: Optional[str] = Field(
        None, max_length=255, description="Summary reference clause or section"
    )


class CoverageRuleCreate(CoverageRuleBase):
    """Schema for persisting a coverage rule."""

    policy_id: int = Field(..., description="ID of associated policy")


class CoverageRuleResponse(CoverageRuleBase):
    """API response schema for coverage rule."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    policy_id: int
    created_at: datetime
    updated_at: datetime
    evidence_references: List[EvidenceReferenceResponse] = []
