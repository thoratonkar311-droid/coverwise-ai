from datetime import datetime
from typing import Any, List, Optional
from pydantic import BaseModel, ConfigDict, Field

from app.schemas.evidence_reference import EvidenceReferenceResponse


class CoverageRuleBase(BaseModel):
    """Base fields for structured coverage rules and policy restrictions."""

    category: Optional[str] = Field(None, max_length=100, description="Rule category e.g. general, procedure, room, waiting_period")
    procedure_name: Optional[str] = Field(None, max_length=255, description="Normalized procedure or treatment name")
    rule_name: Optional[str] = Field(None, max_length=255, description="Descriptive rule name or clause title")
    coverage_status: str = Field(
        default="covered",
        max_length=50,
        description="Coverage determination: covered, not_covered, partially_covered, conditional, not_determined",
    )
    coverage_percentage: Optional[float] = Field(
        None, ge=0.0, le=100.0, description="Contractual coverage percentage (0-100)"
    )
    coverage_limit_amount: Optional[float] = Field(None, ge=0.0, description="Fixed absolute amount cap")
    coverage_limit_percentage_of_si: Optional[float] = Field(
        None, ge=0.0, le=100.0, description="Percentage of sum insured cap"
    )
    unit_frequency: Optional[str] = Field(
        None, max_length=100, description="Limit frequency e.g. per_eye, per_admission, per_year, per_day"
    )
    deductible: Optional[float] = Field(None, ge=0.0, description="Deductible required before coverage kicks in")
    deductible_status: Optional[str] = Field(None, max_length=50, description="Deductible status: specified, waived, not_determined")
    copay: Optional[float] = Field(None, ge=0.0, description="Fixed co-payment amount")
    copay_percentage: Optional[float] = Field(
        None, ge=0.0, le=100.0, description="Co-payment percentage payable by patient"
    )
    coverage_limit: Optional[float] = Field(None, ge=0.0, description="Sum insured or maximum cap on procedure")
    network_condition: Optional[str] = Field(None, max_length=100, description="Network applicability: network_only, non_network, both, all")
    waiting_period: Optional[str] = Field(None, max_length=500, description="Required waiting period before coverage")
    waiting_period_type: Optional[str] = Field(None, max_length=100, description="Type: initial, ped, specific_disease, accidental_waiver")
    room_category: Optional[str] = Field(
        None, max_length=255, description="Eligible hospital room category or rent limitation"
    )
    exclusions: Optional[Any] = Field(None, description="Excluded treatments, conditions, or clauses")
    conditions: Optional[Any] = Field(None, description="Applicable eligibility conditions or sub-limits")
    source_type: Optional[str] = Field(default="contractual_rule", max_length=50, description="Source classification: contractual_rule, statutory, general")
    source_reference: Optional[str] = Field(
        None, max_length=500, description="Summary reference clause or section"
    )
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0, description="Extraction confidence score")


class CoverageRuleCreate(CoverageRuleBase):
    """Schema for persisting a coverage rule."""

    policy_id: int = Field(..., description="ID of associated policy")
    user_id: Optional[str] = Field(None, max_length=100, description="User identifier when auth is active")


class CoverageRuleResponse(CoverageRuleBase):
    """API response schema for coverage rule."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    policy_id: int
    user_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    evidence_references: List[EvidenceReferenceResponse] = []
