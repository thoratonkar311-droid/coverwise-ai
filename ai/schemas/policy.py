"""Insurance policy domain schemas for CoverWise AI.

Defines Pydantic v2 data models for health insurance policies, deductibles,
copayments, coinsurance, benefit categories, clauses, prior authorization rules,
policy limits, waiting periods, and conflicting evidence.

Rule: Unknown or unspecified policy fields MUST default to None (null in JSON).
All citations preserve exact page numbers and evidence spans.
Never infer coverage from missing exclusions.
"""

from enum import Enum
from pydantic import BaseModel, ConfigDict, Field
from ai.schemas.evidence import EvidenceSpan


class CoverageStatus(str, Enum):
    """Status indicating coverage decision."""

    COVERED = "covered"
    NOT_COVERED = "not_covered"
    PARTIALLY_COVERED = "partially_covered"
    PRIOR_AUTHORIZATION_REQUIRED = "prior_authorization_required"
    CONDITIONAL = "conditional"
    UNKNOWN = "unknown"


class CoverageCategory(str, Enum):
    """High-level category of healthcare service."""

    INPATIENT_HOSPITAL = "inpatient_hospital"
    OUTPATIENT_SURGERY = "outpatient_surgery"
    EMERGENCY_ROOM = "emergency_room"
    URGENT_CARE = "urgent_care"
    PRIMARY_CARE = "primary_care"
    SPECIALIST_VISIT = "specialist_visit"
    PRESCRIPTION_DRUGS = "prescription_drugs"
    DIAGNOSTIC_IMAGING = "diagnostic_imaging"
    LAB_SERVICES = "lab_services"
    PREVENTIVE_CARE = "preventive_care"
    MATERNITY_NEWBORN = "maternity_newborn"
    MENTAL_HEALTH = "mental_health"
    DENTAL = "dental"
    VISION = "vision"
    PHYSICAL_THERAPY = "physical_therapy"
    OTHER = "other"


class DeductibleDetails(BaseModel):
    """Annual deductible obligations. Unspecified fields default to None."""

    model_config = ConfigDict(validate_assignment=True)

    individual_in_network: float | None = Field(
        default=None,
        ge=0.0,
        description="Individual in-network deductible amount.",
    )
    individual_out_of_network: float | None = Field(
        default=None,
        ge=0.0,
        description="Individual out-of-network deductible amount.",
    )
    family_in_network: float | None = Field(
        default=None,
        ge=0.0,
        description="Family in-network deductible amount.",
    )
    family_out_of_network: float | None = Field(
        default=None,
        ge=0.0,
        description="Family out-of-network deductible amount.",
    )
    currency: str = Field(default="USD", description="Currency code (e.g. USD, EUR, INR).")
    evidence: list[EvidenceSpan] = Field(
        default_factory=list,
        description="Source evidence supporting the deductible values.",
    )


class CopayDetails(BaseModel):
    """Fixed copayment amounts by service type. Unspecified fields default to None."""

    model_config = ConfigDict(validate_assignment=True)

    primary_care: float | None = Field(
        default=None,
        ge=0.0,
        description="Copayment for in-network primary care physician visit.",
    )
    specialist: float | None = Field(
        default=None,
        ge=0.0,
        description="Copayment for in-network specialist visit.",
    )
    urgent_care: float | None = Field(
        default=None,
        ge=0.0,
        description="Copayment for urgent care center visit.",
    )
    emergency_room: float | None = Field(
        default=None,
        ge=0.0,
        description="Copayment for emergency room services.",
    )
    generic_prescription: float | None = Field(
        default=None,
        ge=0.0,
        description="Copayment for Tier 1 / generic medications.",
    )
    preferred_brand_prescription: float | None = Field(
        default=None,
        ge=0.0,
        description="Copayment for Tier 2 / preferred brand medications.",
    )
    non_preferred_brand_prescription: float | None = Field(
        default=None,
        ge=0.0,
        description="Copayment for Tier 3 / non-preferred brand medications.",
    )
    specialty_drugs: float | None = Field(
        default=None,
        ge=0.0,
        description="Copayment for Tier 4 / specialty drugs.",
    )
    currency: str = Field(default="USD", description="Currency code (e.g. USD).")
    evidence: list[EvidenceSpan] = Field(
        default_factory=list,
        description="Source evidence supporting copayment values.",
    )


class CoinsuranceDetails(BaseModel):
    """Coinsurance percentage splits. Unspecified fields default to None."""

    model_config = ConfigDict(validate_assignment=True)

    in_network_percentage: float | None = Field(
        default=None,
        ge=0.0,
        le=100.0,
        description="Patient coinsurance percentage for in-network care (e.g., 20.0 for 20%).",
    )
    out_of_network_percentage: float | None = Field(
        default=None,
        ge=0.0,
        le=100.0,
        description="Patient coinsurance percentage for out-of-network care.",
    )
    evidence: list[EvidenceSpan] = Field(
        default_factory=list,
        description="Source evidence supporting coinsurance percentages.",
    )


class OutOfPocketMaxDetails(BaseModel):
    """Annual out-of-pocket maximum caps. Unspecified fields default to None."""

    model_config = ConfigDict(validate_assignment=True)

    individual_in_network: float | None = Field(
        default=None,
        ge=0.0,
        description="Individual in-network annual maximum out-of-pocket spend.",
    )
    individual_out_of_network: float | None = Field(
        default=None,
        ge=0.0,
        description="Individual out-of-network annual maximum out-of-pocket spend.",
    )
    family_in_network: float | None = Field(
        default=None,
        ge=0.0,
        description="Family in-network annual maximum out-of-pocket spend.",
    )
    family_out_of_network: float | None = Field(
        default=None,
        ge=0.0,
        description="Family out-of-network annual maximum out-of-pocket spend.",
    )
    currency: str = Field(default="USD", description="Currency code.")
    evidence: list[EvidenceSpan] = Field(
        default_factory=list,
        description="Source evidence supporting out-of-pocket limits.",
    )


class PolicyClause(BaseModel):
    """Specific textual policy clause or provision preserved with page evidence."""

    model_config = ConfigDict(validate_assignment=True)

    clause_id: str = Field(..., description="Unique identifier for the clause.")
    title: str | None = Field(default=None, description="Clause or section title if identified.")
    section_number: str | None = Field(
        default=None,
        description="Section numbering from document (e.g. '3.2(a)').",
    )
    text: str = Field(..., min_length=1, description="Full or excerpted text of the clause.")
    page_number: int = Field(..., ge=1, description="1-indexed page number where clause appears.")
    category: CoverageCategory | str | None = Field(
        default=None,
        description="Service category this clause governs.",
    )
    is_exclusion: bool = Field(default=False, description="Flag indicating if this clause excludes coverage.")
    is_limitation: bool = Field(default=False, description="Flag indicating if this clause imposes limits/caps.")
    evidence: EvidenceSpan | None = Field(
        default=None,
        description="Direct verbatim evidence snippet for this clause.",
    )


class PolicyBenefitItem(BaseModel):
    """Coverage specification for a specific procedure or medical service."""

    model_config = ConfigDict(validate_assignment=True)

    service_name: str = Field(..., min_length=1, description="Standard medical service or procedure name.")
    category: CoverageCategory | str | None = Field(
        default=None,
        description="Category of the medical service.",
    )
    status: CoverageStatus = Field(
        default=CoverageStatus.UNKNOWN,
        description="Coverage classification status.",
    )
    copay_amount: float | None = Field(
        default=None,
        ge=0.0,
        description="Copayment amount required if applicable.",
    )
    coinsurance_percent: float | None = Field(
        default=None,
        ge=0.0,
        le=100.0,
        description="Coinsurance percentage required if applicable.",
    )
    deductible_applies: bool | None = Field(
        default=None,
        description="Whether deductible must be satisfied before coverage begins.",
    )
    prior_authorization_required: bool | None = Field(
        default=None,
        description="Whether prior authorization is mandated for this service.",
    )
    referral_required: bool | None = Field(
        default=None,
        description="Whether primary care physician referral is required.",
    )
    limits_and_exceptions: str | None = Field(
        default=None,
        description="Text summary of visit caps, day limits, or restrictions.",
    )
    evidence: list[EvidenceSpan] = Field(
        default_factory=list,
        description="Verbatim citations and page references for this benefit.",
    )


class WaitingPeriodInfo(BaseModel):
    """Waiting period stipulations for specific conditions or benefits."""

    model_config = ConfigDict(validate_assignment=True)

    condition_or_benefit: str = Field(..., description="Condition, treatment, or benefit subject to wait.")
    duration_days: int | None = Field(default=None, ge=0, description="Duration in calendar days if stated.")
    duration_months: int | None = Field(default=None, ge=0, description="Duration in months if stated.")
    description: str = Field(..., description="Full text explanation of waiting period requirements.")
    evidence: list[EvidenceSpan] = Field(
        default_factory=list,
        description="Source evidence citations preserving page numbers.",
    )


class PriorAuthorizationRule(BaseModel):
    """Structured prior authorization requirements."""

    model_config = ConfigDict(validate_assignment=True)

    service_or_procedure: str = Field(..., description="Medical procedure or service requiring prior approval.")
    timeline_requirement: str | None = Field(
        default=None,
        description="Submission deadline (e.g. 'at least 72 hours prior to elective admission').",
    )
    approving_entity: str | None = Field(
        default=None,
        description="Governing review body (e.g. 'Medical Review Board').",
    )
    details: str = Field(..., description="Details and consequences of non-compliance.")
    evidence: list[EvidenceSpan] = Field(
        default_factory=list,
        description="Verbatim citations and page references.",
    )


class PolicyLimit(BaseModel):
    """Quantitative or temporal policy limitation (visit caps, dollar ceilings)."""

    model_config = ConfigDict(validate_assignment=True)

    service_or_category: str = Field(..., description="Service or benefit subject to the limit.")
    limit_type: str = Field(..., description="Type of limit (e.g. 'visit_limit', 'dollar_cap', 'day_limit').")
    limit_value: str = Field(..., description="Expressed limit (e.g. '12 visits annually', '$250 max').")
    details: str = Field(..., description="Context and operational rules governing the limit.")
    evidence: list[EvidenceSpan] = Field(
        default_factory=list,
        description="Verbatim citations and page numbers.",
    )


class ExclusionItem(BaseModel):
    """Structured policy exclusion item."""

    model_config = ConfigDict(validate_assignment=True)

    category_or_service: str = Field(..., description="Treatment, category, or service excluded from coverage.")
    description: str = Field(..., description="Full text description of the exclusion.")
    exceptions_or_conditions: str | None = Field(
        default=None,
        description="Exceptions where coverage may apply (e.g. severe medical necessity criteria).",
    )
    evidence: list[EvidenceSpan] = Field(
        default_factory=list,
        description="Verbatim citations and page numbers.",
    )


class ConflictingEvidence(BaseModel):
    """Records conflicting or ambiguous clauses discovered during document parsing."""

    model_config = ConfigDict(validate_assignment=True)

    field_or_clause: str = Field(..., description="The policy provision or field with conflicting terms.")
    description: str = Field(..., description="Explanation of the discrepancy or conflict.")
    conflicting_spans: list[EvidenceSpan] = Field(
        default_factory=list,
        description="List of divergent evidence spans with their respective page numbers.",
    )
    notes: str | None = Field(default=None, description="Resolution notes or escalation recommendation.")


class PolicyDocumentMetadata(BaseModel):
    """Metadata identifying the policy document. Unknown fields default to None."""

    model_config = ConfigDict(validate_assignment=True)

    policy_id: str | None = Field(default=None, description="System or insurer policy ID.")
    policy_name: str | None = Field(default=None, description="Plan or policy marketing name.")
    insurer_name: str | None = Field(default=None, description="Insurance provider/payer company name.")
    plan_type: str | None = Field(
        default=None,
        description="Insurance plan type (e.g. HMO, PPO, EPO, POS, HDHP).",
    )
    plan_year: int | None = Field(
        default=None,
        ge=2000,
        le=2100,
        description="Applicable plan calendar year.",
    )
    effective_date: str | None = Field(default=None, description="Plan effective start date.")
    expiration_date: str | None = Field(default=None, description="Plan expiration/renewal date.")
    network_name: str | None = Field(default=None, description="Associated provider network name.")


class PolicyAnalysis(BaseModel):
    """Consolidated structured analysis of an extracted policy document."""

    model_config = ConfigDict(validate_assignment=True)

    raw_document_id: str | None = Field(
        default=None,
        description="Reference to source ExtractedDocument ID.",
    )
    metadata: PolicyDocumentMetadata = Field(
        default_factory=PolicyDocumentMetadata,
        description="Policy identification metadata.",
    )
    currency: str = Field(
        default="USD",
        description="Standard currency used for policy obligations.",
    )
    deductibles: DeductibleDetails = Field(
        default_factory=DeductibleDetails,
        description="Deductible thresholds.",
    )
    copays: CopayDetails = Field(
        default_factory=CopayDetails,
        description="Standard copayments.",
    )
    coinsurance: CoinsuranceDetails = Field(
        default_factory=CoinsuranceDetails,
        description="Coinsurance rates.",
    )
    out_of_pocket_max: OutOfPocketMaxDetails = Field(
        default_factory=OutOfPocketMaxDetails,
        description="Maximum out of pocket limitations.",
    )
    benefits: list[PolicyBenefitItem] = Field(
        default_factory=list,
        description="Itemized coverage benefits.",
    )
    clauses: list[PolicyClause] = Field(
        default_factory=list,
        description="Extracted policy clauses and restrictions.",
    )
    exclusions: list[str] = Field(
        default_factory=list,
        description="Explicit list of excluded treatments or conditions.",
    )
    detailed_exclusions: list[ExclusionItem] = Field(
        default_factory=list,
        description="Structured exclusion items with verbatim page evidence.",
    )
    prior_authorizations: list[PriorAuthorizationRule] = Field(
        default_factory=list,
        description="Prior authorization mandates and deadlines.",
    )
    limits: list[PolicyLimit] = Field(
        default_factory=list,
        description="Quantitative visit and monetary limits.",
    )
    waiting_periods: list[WaitingPeriodInfo] = Field(
        default_factory=list,
        description="Waiting period requirements if stated.",
    )
    conflicting_evidence: list[ConflictingEvidence] = Field(
        default_factory=list,
        description="Identified conflicting clauses across sections.",
    )
    extracted_at: str | None = Field(
        default=None,
        description="Timestamp when the analysis was generated.",
    )
    extraction_source: str = Field(
        default="hybrid",
        description="Extraction method: 'ollama', 'deterministic', or 'hybrid'.",
    )
