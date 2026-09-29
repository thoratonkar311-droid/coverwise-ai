from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


CoverageStatusType = Literal["likely_covered", "partially_covered", "not_covered", "not_determined"]
VALID_COVERAGE_STATUSES = {"likely_covered", "partially_covered", "not_covered", "not_determined"}


class DocumentExtractionInput(BaseModel):
    """Payload provided to AI/OCR pipeline to extract policy document information."""

    filename: str = Field(..., min_length=1, max_length=255, description="Document filename")
    file_path: Optional[str] = Field(None, max_length=500, description="Local or object storage path")
    content_type: Optional[str] = Field("application/pdf", description="MIME content type")
    raw_text: Optional[str] = Field(None, description="Optional pre-extracted text from document")


class ExtractedPolicyInfo(BaseModel):
    """Structured high-level policy document metadata extracted by Member 3's AI pipeline."""

    model_config = ConfigDict(from_attributes=True)

    insurer_name: Optional[str] = Field(None, max_length=255, description="Insurance provider name")
    plan_name: Optional[str] = Field(None, max_length=255, description="Insurance plan or policy product name")
    policy_number: Optional[str] = Field(None, max_length=100, description="Unique policy identifier")
    policy_holder_name: Optional[str] = Field(None, max_length=255, description="Insured person name")
    sum_insured: Optional[float] = Field(None, ge=0.0, description="Base annual sum insured")
    validity_period: Optional[str] = Field(None, description="Policy validity or term range")
    summary: Optional[str] = Field(None, description="Executive narrative summary of policy coverage")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Raw parser / OCR metadata")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0, description="Overall document parsing confidence")


class EvidenceItem(BaseModel):
    """Verifiable citation linking an AI interpretation or coverage rule directly to source policy text."""

    model_config = ConfigDict(from_attributes=True)

    document_source: str = Field(..., max_length=255, description="Source document filename or identifier")
    page: Optional[int] = Field(None, ge=1, description="Page number of citation")
    clause_section: Optional[str] = Field(None, max_length=255, description="Clause title, section, or paragraph")
    extracted_text: Optional[str] = Field(None, description="Exact quotation verbatim from policy document")
    interpretation: Optional[str] = Field(None, description="Plain-language AI interpretation of how clause impacts coverage")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0, description="Model extraction confidence score")
    source_type: str = Field(default="contractual_rule", description="Source classification: contractual_rule, example, estimate, explanation, exclusion, definition")


class StructuredPolicyRules(BaseModel):
    """
    Normalized, machine-readable coverage rules extracted from policy language.

    The deterministic CalculationService consumes strictly these typed numeric parameters.
    No unstructured model text is permitted to bypass these rules.
    """

    model_config = ConfigDict(from_attributes=True)

    deductible: Optional[float] = Field(None, ge=0.0, description="Deductible required before coverage kicks in")
    copay_fixed: Optional[float] = Field(None, ge=0.0, description="Fixed co-payment amount")
    copay_percentage: Optional[float] = Field(
        None, ge=0.0, le=100.0, description="Co-payment percentage payable by patient"
    )
    coverage_limit: Optional[float] = Field(None, ge=0.0, description="Procedure sub-limit or cap")
    room_rent_limit: Optional[float] = Field(None, ge=0.0, description="Daily room rent sub-limit or cap")
    room_category_allowed: Optional[str] = Field(
        None, max_length=100, description="Allowed hospital room category (e.g., Single Private, Twin Sharing)"
    )
    exclusions: List[str] = Field(default_factory=list, description="Non-payable items or treatment conditions")
    waiting_periods: Optional[str] = Field(None, description="Applicable waiting period terms")
    has_policy_rules: bool = Field(True, description="Whether specific rules were found in document")


class CoverageAnalysisInput(BaseModel):
    """Typed request contract passed to AI policy analysis service."""

    treatment_name: str = Field(..., min_length=1, max_length=255, description="Target medical procedure")
    treatment_category: Optional[str] = Field(None, max_length=100, description="Optional clinical category")
    hospital_quote: Optional[float] = Field(None, gt=0.0, description="Optional estimated hospital quote")
    room_category: Optional[str] = Field(None, max_length=100, description="Patient requested room category")
    policy_id: Optional[int] = Field(None, gt=0, description="Database ID of policy")
    policy_info: Optional[ExtractedPolicyInfo] = Field(None, description="Extracted policy information")


class StructuredAIAnalysisResult(BaseModel):
    """
    Standardized, strictly typed AI output contract for Member 3's AI/ML pipeline.

    Enforces separation of AI interpretation (clauses, coverage status, explanations)
    from deterministic calculation (rules, caps, deductibles).
    """

    model_config = ConfigDict(from_attributes=True)

    coverage_status: str = Field(
        ...,
        description="Coverage status: 'likely_covered', 'partially_covered', 'not_covered', 'not_determined'",
    )
    coverage_information: str = Field(..., description="High-level narrative findings")
    rules: StructuredPolicyRules = Field(
        default_factory=StructuredPolicyRules,
        description="Structured numeric coverage rules for deterministic financial engine",
    )
    exclusions: List[str] = Field(default_factory=list, description="Relevant exclusions")
    waiting_periods: Optional[str] = Field(None, description="Applicable waiting periods")
    evidence: List[EvidenceItem] = Field(
        default_factory=list,
        description="Traceable citations supporting extracted rules and coverage determinations",
    )
    confidence: float = Field(..., ge=0.0, le=1.0, description="AI extraction confidence score (0.0 - 1.0)")
    warnings: List[str] = Field(default_factory=list, description="Warnings regarding sub-limits or missing clauses")
    explanation: str = Field(..., description="Plain-language explanation of findings for patient")
    raw_ai_metadata: Dict[str, Any] = Field(default_factory=dict, description="Model debug info / prompt tokens")

    @field_validator("coverage_status")
    @classmethod
    def validate_coverage_status(cls, v: str) -> str:
        clean = v.strip().lower()
        if clean not in VALID_COVERAGE_STATUSES:
            raise ValueError(
                f"Invalid coverage_status '{v}'. Must be one of: {', '.join(sorted(VALID_COVERAGE_STATUSES))}"
            )
        return clean

    @model_validator(mode="after")
    def validate_not_determined_integrity(self) -> "StructuredAIAnalysisResult":
        """
        Adheres strictly to the core principle:
        'Do not invent policy facts. If no reliable policy rule is available, return not_determined.'
        """
        if self.coverage_status == "not_determined":
            if not self.explanation.strip():
                raise ValueError("An explanation is required when coverage_status is 'not_determined'.")
            if self.confidence > 0.5:
                # Cap confidence for not_determined determinations
                self.confidence = 0.5
        return self


class EvidenceQueryInput(BaseModel):
    """Payload to retrieve supporting policy clauses and evidence citations via RAG."""

    policy_id: Optional[int] = Field(None, gt=0, description="Database ID of policy")
    document_source: Optional[str] = Field(None, max_length=255, description="Document identifier or filename")
    query: str = Field(..., min_length=2, max_length=500, description="Question or clause concept to query")
    max_results: int = Field(default=5, ge=1, le=20, description="Maximum evidence items to return")


class EvidenceRetrievalOutput(BaseModel):
    """Response contract returning citations and matching policy clauses."""

    query: str
    evidence_items: List[EvidenceItem] = Field(default_factory=list)
    summary: Optional[str] = None
