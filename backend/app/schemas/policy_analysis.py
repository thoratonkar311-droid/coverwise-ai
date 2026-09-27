from datetime import datetime
from typing import Any, List, Optional
from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.evidence_reference import EvidenceReferenceResponse


class AnalysisRequest(BaseModel):
    """Request payload to initiate policy coverage analysis for a treatment."""

    policy_id: int = Field(..., gt=0, description="ID of policy to analyze")
    treatment_name: Optional[str] = Field(None, min_length=1, max_length=255, description="Treatment or procedure name")
    treatment: Optional[str] = Field(None, min_length=1, max_length=255, description="Alias for treatment_name")
    treatment_id: Optional[int] = Field(None, gt=0, description="Optional catalog treatment ID")
    force_refresh: bool = Field(default=False, description="Force re-running analysis even if cached result exists")

    @model_validator(mode="after")
    def sync_treatment(self) -> "AnalysisRequest":
        if not self.treatment_name and self.treatment:
            self.treatment_name = self.treatment
        elif not self.treatment and self.treatment_name:
            self.treatment = self.treatment_name
        if not self.treatment_name:
            raise ValueError("Either treatment_name or treatment must be provided.")
        return self


class AnalysisCreate(BaseModel):
    """Schema for persisting an analysis record."""

    policy_id: int = Field(..., description="Target policy ID")
    treatment_id: Optional[int] = Field(None, description="Target treatment ID")
    treatment_name: Optional[str] = Field(None, max_length=255, description="Treatment name")
    status: str = Field(default="completed", max_length=50, description="Analysis lifecycle state")
    result_summary: Optional[str] = Field(None, description="Executive narrative summary")
    result_data: Optional[Any] = Field(None, description="Detailed JSON result with math and clauses")


class CoverageResult(BaseModel):
    """Standardized coverage assessment output."""

    status: str = Field(
        ...,
        description="Coverage status: likely_covered, partially_covered, not_determined, not_covered",
    )
    information: str = Field(..., description="Detailed coverage findings")
    deductible: Optional[float] = Field(None, ge=0.0, description="Applicable deductible amount")
    copay: Optional[float] = Field(None, ge=0.0, description="Fixed co-payment amount")
    copay_percentage: Optional[float] = Field(None, ge=0.0, le=100.0, description="Co-payment percentage")
    coverage_limit: Optional[float] = Field(None, ge=0.0, description="Procedure sub-limit or sum insured cap")
    exclusions: List[str] = Field(default_factory=list, description="Relevant policy exclusions")
    waiting_periods: Optional[str] = Field(None, description="Applicable waiting periods")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Extraction confidence score (0.0 to 1.0)")
    explanation: str = Field(..., description="Plain-language explanation of findings")


class AnalysisDetailResponse(BaseModel):
    """Full detail view of an analysis result."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    policy_id: int
    treatment_id: Optional[int] = None
    treatment_name: str
    status: str
    coverage_status: str
    coverage_information: str
    deductible: Optional[float] = None
    copay: Optional[float] = None
    copay_percentage: Optional[float] = None
    coverage_limit: Optional[float] = None
    exclusions: List[str] = Field(default_factory=list)
    waiting_periods: Optional[str] = None
    confidence: float = 0.0
    explanation: str
    evidence_references: List[EvidenceReferenceResponse] = []
    created_at: datetime
    updated_at: datetime


class AnalysisResponse(BaseModel):
    """Legacy/generic analysis response model."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    policy_id: int
    treatment_id: Optional[int] = None
    treatment_name: Optional[str] = None
    status: str
    result_summary: Optional[str] = None
    result_data: Optional[Any] = None
    created_at: datetime
    updated_at: datetime
    evidence_references: List[EvidenceReferenceResponse] = []
