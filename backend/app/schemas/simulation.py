from datetime import datetime
from typing import Any, List, Optional
from pydantic import BaseModel, ConfigDict, Field, model_validator


class SimulationRequest(BaseModel):
    """Request payload for running a deterministic cost simulation."""

    policy_id: Optional[int] = Field(None, gt=0, description="Policy ID to calculate against")
    treatment: Optional[str] = Field(None, max_length=255, description="Treatment name or identifier")
    treatment_name: Optional[str] = Field(None, max_length=255, description="Treatment name alias")
    treatment_id: Optional[int] = Field(None, gt=0, description="Catalog treatment ID if known")
    hospital_quote: float = Field(..., gt=0.0, description="Estimated total hospital quote or medical bill")
    room_category: Optional[str] = Field(None, max_length=100, description="Patient chosen room category")
    non_payable_items: Optional[float] = Field(None, ge=0.0, description="Estimated non-payable items or consumables")
    deductible: Optional[float] = Field(None, ge=0.0, description="Deductible override or input")
    copay: Optional[float] = Field(None, ge=0.0, description="Fixed co-payment amount override")
    copay_percentage: Optional[float] = Field(None, ge=0.0, le=100.0, description="Co-payment percentage override")
    coverage_limit: Optional[float] = Field(None, ge=0.0, description="Coverage limit or sum insured override")
    is_network_hospital: Optional[bool] = Field(True, description="Whether hospital is in-network")

    @model_validator(mode="before")
    @classmethod
    def normalize_aliases(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if data.get("is_network_hospital") is None:
                for k in ("isNetworkHospital", "network", "is_network"):
                    if data.get(k) is not None:
                        data["is_network_hospital"] = data[k]
                        break
            if data.get("hospital_quote") is None:
                for k in ("hospitalQuote", "quote", "billed_amount", "cost"):
                    if data.get(k) is not None:
                        data["hospital_quote"] = data[k]
                        break
            if data.get("copay_percentage") is None:
                for k in ("copayPercent", "copay_pct", "copay_percent"):
                    if data.get(k) is not None:
                        data["copay_percentage"] = data[k]
                        break
            if data.get("coverage_limit") is None and data.get("coverageLimit") is not None:
                data["coverage_limit"] = data["coverageLimit"]
            if data.get("non_payable_items") is None:
                for k in ("consumablesEstimate", "consumables", "nonPayableItems"):
                    if data.get(k) is not None:
                        data["non_payable_items"] = data[k]
                        break
            if not data.get("room_category"):
                for k in ("roomCategory", "room_tier", "room"):
                    if data.get(k):
                        data["room_category"] = data[k]
                        break
            if data.get("policy_id") is None and data.get("policyId") is not None:
                try:
                    data["policy_id"] = int(data["policyId"])
                except (ValueError, TypeError):
                    pass
        return data

    @model_validator(mode="after")
    def sync_treatment_name(self) -> "SimulationRequest":
        """Ensure either treatment or treatment_name populates the other."""
        if self.treatment and not self.treatment_name:
            self.treatment_name = self.treatment
        elif self.treatment_name and not self.treatment:
            self.treatment = self.treatment_name
        return self


class SimulationResponse(BaseModel):
    """Response representing deterministic financial distribution between patient and insurer."""

    model_config = ConfigDict(from_attributes=True)

    id: Optional[int] = None
    policy_id: Optional[int] = None
    treatment: Optional[str] = None
    treatment_name: Optional[str] = None
    hospital_quote: Optional[float] = Field(None, description="Original hospital quote")
    total_treatment_cost: Optional[float] = Field(None, description="Total treatment cost / hospital quote")
    room_category: Optional[str] = Field(None, description="Patient chosen room category")
    estimated_insurance_share: float = Field(..., description="Portion payable by insurance")
    estimated_patient_share: float = Field(..., description="Portion payable out-of-pocket by patient")
    deductible: float = Field(default=0.0, description="Deductible amount applied")
    copay: float = Field(default=0.0, description="Co-payment amount applied")
    coverage_applied: float = Field(default=0.0, description="Net eligible amount covered")
    excluded_amount: float = Field(default=0.0, description="Non-payable / excluded amount")
    assumptions: List[str] = Field(default_factory=list, description="Explicit calculation assumptions")
    warnings: List[str] = Field(default_factory=list, description="Warnings regarding sub-limits or conditions")
    calculation_breakdown: Optional[Any] = None
    created_at: Optional[datetime] = None

    @model_validator(mode="before")
    @classmethod
    def populate_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            quote = data.get("hospital_quote") if data.get("hospital_quote") is not None else data.get("total_treatment_cost")
            if data.get("hospital_quote") is None and quote is not None:
                data["hospital_quote"] = quote
            if data.get("total_treatment_cost") is None and quote is not None:
                data["total_treatment_cost"] = quote
            t_name = data.get("treatment_name") or data.get("treatment")
            if data.get("treatment_name") is None and t_name is not None:
                data["treatment_name"] = t_name
            if data.get("treatment") is None and t_name is not None:
                data["treatment"] = t_name
        return data

    @model_validator(mode="after")
    def sync_fields(self) -> "SimulationResponse":
        quote = self.hospital_quote if self.hospital_quote is not None else self.total_treatment_cost
        if self.hospital_quote is None and quote is not None:
            self.hospital_quote = quote
        if self.total_treatment_cost is None and quote is not None:
            self.total_treatment_cost = quote
        t_name = self.treatment_name or self.treatment
        if self.treatment_name is None and t_name is not None:
            self.treatment_name = t_name
        if self.treatment is None and t_name is not None:
            self.treatment = t_name
        return self
