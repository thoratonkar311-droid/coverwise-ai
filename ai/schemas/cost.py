"""Cost calculation and patient responsibility schemas for CoverWise AI.

Represents treatment cost estimations, insurer vs patient splits,
calculation breakdowns, and legal/policy citations.
"""

from pydantic import BaseModel, ConfigDict, Field
from ai.schemas.evidence import Citation
from ai.schemas.policy import CoverageStatus, PolicyClause


class CostBreakdownItem(BaseModel):
    """Line item in a treatment cost estimation."""

    model_config = ConfigDict(frozen=True)

    description: str = Field(..., description="Description of the cost component.")
    amount: float = Field(..., ge=0.0, description="Amount in local currency.")
    paid_by: str = Field(..., description="'patient' or 'insurer'.")


class TreatmentCostEstimate(BaseModel):
    """Comprehensive estimate of treatment cost and responsibility distribution.

    Unknown numeric values default to None (null).
    """

    model_config = ConfigDict(validate_assignment=True)

    treatment_name: str = Field(..., min_length=1, description="Target medical treatment or procedure.")
    treatment_code: str | None = Field(
        default=None,
        description="Standard medical procedure code (CPT, HCPCS, ICD-10) if provided.",
    )
    in_network: bool = Field(default=True, description="Whether treatment is modeled as in-network.")
    status: CoverageStatus = Field(
        default=CoverageStatus.UNKNOWN,
        description="Coverage classification status.",
    )

    # Core cost estimates
    estimated_total_cost: float | None = Field(
        default=None,
        ge=0.0,
        description="Total billed or negotiated cost for the treatment.",
    )
    estimated_insurer_responsibility: float | None = Field(
        default=None,
        ge=0.0,
        description="Estimated amount covered by the insurance payer.",
    )
    estimated_patient_responsibility: float | None = Field(
        default=None,
        ge=0.0,
        description="Estimated out-of-pocket amount owed by the patient.",
    )

    # Patient responsibility component breakdowns
    estimated_deductible_applied: float | None = Field(
        default=None,
        ge=0.0,
        description="Portion of patient cost attributed to annual deductible.",
    )
    estimated_copay_applied: float | None = Field(
        default=None,
        ge=0.0,
        description="Fixed copay applied to this treatment.",
    )
    estimated_coinsurance_applied: float | None = Field(
        default=None,
        ge=0.0,
        description="Percentage coinsurance applied after deductible.",
    )
    currency: str = Field(default="USD", description="Currency identifier.")

    # Audit trail, clauses, and warnings
    calculation_steps: list[str] = Field(
        default_factory=list,
        description="Step-by-step mathematical explanation of the cost calculation.",
    )
    supporting_clauses: list[PolicyClause] = Field(
        default_factory=list,
        description="Policy clauses supporting this coverage determination.",
    )
    citations: list[Citation] = Field(
        default_factory=list,
        description="Verbatim citations with document and page numbers.",
    )
    assumptions_and_warnings: list[str] = Field(
        default_factory=list,
        description="Crucial caveats (e.g. prior auth required, network limitations).",
    )
    requires_prior_authorization: bool | None = Field(
        default=None,
        description="Whether prior authorization is mandatory before treatment.",
    )
