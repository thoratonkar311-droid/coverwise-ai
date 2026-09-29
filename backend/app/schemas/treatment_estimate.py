from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, model_validator

from app.services.treatment_estimation_service import (
    DrivingFactor,
    TreatmentScenarioInput,
)


class TreatmentEstimateRequest(BaseModel):
    """Payload to request deterministic treatment cost and coverage estimation."""

    policy_id: Optional[int] = Field(None, description="Database ID of the active policy")
    scenario: Optional[TreatmentScenarioInput] = None

    @model_validator(mode="before")
    @classmethod
    def populate_scenario(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "policy_id" in data and isinstance(data["policy_id"], str):
                try:
                    data["policy_id"] = int(data["policy_id"])
                except (ValueError, TypeError):
                    data["policy_id"] = None
            if "policyId" in data and not data.get("policy_id"):
                try:
                    data["policy_id"] = int(data["policyId"])
                except (ValueError, TypeError):
                    data["policy_id"] = None

            if not data.get("scenario"):
                scenario_data = dict(data)
                scenario_data.pop("policy_id", None)
                scenario_data.pop("policyId", None)
                data["scenario"] = scenario_data
        return data


class WhatIfRequest(BaseModel):
    """Payload to request What-If comparison across two scenario states."""

    policy_id: Optional[int] = Field(None, description="Database ID of the active policy")
    previous_scenario: TreatmentScenarioInput
    updated_scenario: TreatmentScenarioInput

    @model_validator(mode="before")
    @classmethod
    def normalize_what_if(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "policy_id" in data and isinstance(data["policy_id"], str):
                try:
                    data["policy_id"] = int(data["policy_id"])
                except (ValueError, TypeError):
                    data["policy_id"] = None
            if "policyId" in data and not data.get("policy_id"):
                try:
                    data["policy_id"] = int(data["policyId"])
                except (ValueError, TypeError):
                    data["policy_id"] = None
            if "previousScenario" in data and "previous_scenario" not in data:
                data["previous_scenario"] = data["previousScenario"]
            if "updatedScenario" in data and "updated_scenario" not in data:
                data["updated_scenario"] = data["updatedScenario"]
        return data


class TreatmentEstimateResponse(BaseModel):
    """Structured response for treatment cost estimation."""

    treatment_name: str
    benchmark_treatment_id: Optional[str] = None
    currency: str = "INR"
    is_benchmark_matched: bool = False
    benchmark_typical_cost: Optional[float] = None
    benchmark_cost_range: Optional[Dict[str, float]] = None

    estimated_total_cost: float
    potentially_eligible_amount: float
    estimated_insurer_contribution: float
    estimated_patient_responsibility: float

    deductible_applied: float = 0.0
    deductible_status: str = "determined"
    deductible_amount: Optional[float] = None
    is_conditional_on_deductible: bool = False
    policy_coverage_percentage: Optional[float] = None
    policy_coverage_cap: Optional[float] = None
    copay_applied: float = 0.0
    applicable_copay_percentage: Optional[float] = None
    excess_over_limit: float = 0.0
    non_payable_excluded: float = 0.0
    room_rent_penalty: float = 0.0
    calculation_trace: List[str] = Field(default_factory=list)

    confidence_level: str
    coverage_status: str
    driving_factors: List[DrivingFactor] = Field(default_factory=list)
    missing_information: List[str] = Field(default_factory=list)
    uncertainty_notes: List[str] = Field(default_factory=list)
    assumptions: List[str] = Field(default_factory=list)
    disclaimer: str
    raw_calculation: Dict[str, Any] = Field(default_factory=dict)



class WhatIfResponse(BaseModel):
    """Structured response explaining parameter changes and financial impact."""

    previous_scenario: Dict[str, Any]
    updated_scenario: Dict[str, Any]
    previous_estimate: TreatmentEstimateResponse
    updated_estimate: TreatmentEstimateResponse
    changes_detected: List[str]
    total_cost_delta: float
    insurer_contribution_delta: float
    patient_responsibility_delta: float
    explanation_of_changes: List[str]
