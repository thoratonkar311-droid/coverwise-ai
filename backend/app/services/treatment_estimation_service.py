import logging
import re
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, model_validator

from app.models.policy import Policy
from app.services.calculation_service import (
    CalculationInput,
    CalculationResult,
    CalculationService,
    PolicyRulesInput,
)
from app.services.treatment_catalog_service import (
    TreatmentCatalogService,
    get_treatment_catalog_service,
)

logger = logging.getLogger("coverwise.services.treatment_estimation")


class TreatmentScenarioInput(BaseModel):
    """Structured user scenario for treatment cost estimation."""

    treatment_name: str = Field(..., description="Name or description of treatment/procedure")
    diagnosis: Optional[str] = Field(None, description="Primary medical diagnosis or condition")
    hospital_name: Optional[str] = Field(None, description="Hospital or medical facility name")
    city: Optional[str] = Field(None, description="City or geographic location")
    hospital_type: Optional[str] = Field(None, description="Network / Multi-specialty / Daycare tier")
    inpatient_outpatient: Optional[str] = Field("inpatient", description="inpatient or outpatient")
    length_of_stay_days: Optional[int] = Field(None, ge=0, description="Estimated length of stay in days")
    patient_age: Optional[int] = Field(None, ge=0, le=120, description="Patient age in years")
    quoted_cost: Optional[float] = Field(None, ge=0, description="Hospital quoted cost or estimate")
    non_payable_items: Optional[float] = Field(0.0, ge=0, description="Estimated non-payable items/consumables")
    room_category: Optional[str] = Field(None, description="Room category e.g. Single Private, Twin Sharing")
    room_rent_daily: Optional[float] = Field(None, ge=0, description="Daily room rent charged by hospital")
    is_network_hospital: bool = Field(True, description="Whether hospital is in insurer network")
    waiting_period_served: Optional[bool] = Field(None, description="Whether policy waiting period has been completed")
    pre_existing_condition: bool = Field(False, description="Whether condition is pre-existing")

    @model_validator(mode="before")
    @classmethod
    def normalize_aliases(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if data.get("pre_existing_condition") is None:
                for key in ("pre_existing", "preExisting", "preExistingCondition"):
                    if data.get(key) is not None:
                        data["pre_existing_condition"] = bool(data[key])
                        break
            # Normalize treatment / procedure name
            if not data.get("treatment_name"):
                for key in ("procedure_name", "procedure", "treatment", "name"):
                    if data.get(key):
                        data["treatment_name"] = str(data[key])
                        break
            # Normalize quoted cost
            if data.get("quoted_cost") is None:
                for key in ("hospital_quote", "quote", "cost", "billed_amount", "hospitalQuote"):
                    if data.get(key) is not None:
                        try:
                            data["quoted_cost"] = float(data[key])
                            break
                        except (ValueError, TypeError):
                            pass
            # Normalize room category
            if not data.get("room_category"):
                for key in ("room_tier", "room", "roomTier", "roomCategory"):
                    if data.get(key):
                        data["room_category"] = str(data[key])
                        break
            # Normalize hospital type
            if not data.get("hospital_type"):
                for key in ("hospital_tier", "tier", "facility_tier", "hospitalTier", "hospitalType"):
                    if data.get(key):
                        data["hospital_type"] = str(data[key])
                        break
            # Normalize non-payable items
            if data.get("non_payable_items") is None:
                for key in ("consumables_estimate", "consumables", "nonPayableItems"):
                    if data.get(key) is not None:
                        try:
                            data["non_payable_items"] = float(data[key])
                            break
                        except (ValueError, TypeError):
                            pass
            # Normalize stay days
            if data.get("length_of_stay_days") is None:
                for key in ("stay", "stay_days", "lengthOfStayDays"):
                    if data.get(key) is not None:
                        try:
                            data["length_of_stay_days"] = int(data[key])
                            break
                        except (ValueError, TypeError):
                            pass
            # Normalize patient age
            if data.get("patient_age") is None:
                for key in ("age", "patientAge"):
                    if data.get(key) is not None:
                        try:
                            data["patient_age"] = int(data[key])
                            break
                        except (ValueError, TypeError):
                            pass
            # Default treatment_name if still missing but quote provided
            if not data.get("treatment_name"):
                data["treatment_name"] = "General Inpatient Hospitalization"
        return data


class DrivingFactor(BaseModel):
    """Detailed explanatory driver of the financial estimate."""

    factor_name: str
    impact_amount: Optional[float] = None
    description: str
    citation: Optional[str] = None


class TreatmentCostEstimateResult(BaseModel):
    """Complete auditable treatment cost and coverage estimation result."""

    treatment_name: str
    benchmark_treatment_id: Optional[str] = None
    currency: str = "INR"
    is_benchmark_matched: bool = False
    benchmark_typical_cost: Optional[float] = None
    benchmark_cost_range: Optional[Dict[str, float]] = None

    # Financial breakdown
    estimated_total_cost: float
    potentially_eligible_amount: float
    estimated_insurer_contribution: float
    estimated_patient_responsibility: float

    # Factor details
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

    # Qualitative explanation and trust
    confidence_level: str  # "High", "Medium", "Low", "Insufficient evidence"
    coverage_status: str  # "likely_covered", "partially_covered", "not_determined", "not_covered"
    driving_factors: List[DrivingFactor] = Field(default_factory=list)
    missing_information: List[str] = Field(default_factory=list)
    uncertainty_notes: List[str] = Field(default_factory=list)
    assumptions: List[str] = Field(default_factory=list)
    disclaimer: str = (
        "Estimate — not insurer authorization. Final claim admissibility is subject to policy conditions, "
        "medical necessity evaluation, and insurer/TPA adjudication."
    )
    raw_calculation: Dict[str, Any] = Field(default_factory=dict)


class WhatIfComparisonResult(BaseModel):
    """Comparison explaining how estimates and liabilities change across scenario modifications."""

    previous_scenario: Dict[str, Any]
    updated_scenario: Dict[str, Any]
    previous_estimate: TreatmentCostEstimateResult
    updated_estimate: TreatmentCostEstimateResult
    changes_detected: List[str]
    total_cost_delta: float
    insurer_contribution_delta: float
    patient_responsibility_delta: float
    explanation_of_changes: List[str]


class TreatmentCostEstimationService:
    """Service combining policy rules, patient scenario, and synthetic benchmark dataset deterministically."""

    def __init__(
        self,
        catalog_service: Optional[TreatmentCatalogService] = None,
    ) -> None:
        self.catalog = catalog_service or get_treatment_catalog_service()

    def estimate(
        self,
        scenario: TreatmentScenarioInput,
        policy_rules: Optional[PolicyRulesInput] = None,
        policy: Optional[Policy] = None,
    ) -> TreatmentCostEstimateResult:
        """Calculate deterministic treatment expense and patient out-of-pocket breakdown."""
        driving_factors: List[DrivingFactor] = []
        missing_info: List[str] = []
        uncertainty_notes: List[str] = []
        assumptions: List[str] = []

        # 1. Match benchmark dataset
        benchmark = self.catalog.find_treatment(scenario.treatment_name)
        benchmark_id = benchmark.get("treatment_id") if benchmark else None
        currency = benchmark.get("currency", "INR") if benchmark else "INR"
        is_matched = benchmark is not None

        benchmark_typical = benchmark.get("typical_cost") if benchmark else None
        benchmark_range = (
            {"min": benchmark["min_cost"], "max": benchmark["max_cost"]}
            if benchmark
            else None
        )

        # 2. Determine effective treatment cost
        if scenario.quoted_cost is not None and scenario.quoted_cost > 0:
            effective_cost = float(scenario.quoted_cost)
            assumptions.append(f"Estimated cost based on user-supplied hospital quote of {effective_cost:,.2f} {currency}.")
        else:
            # Benchmark vs Actual Hospital Quote (Requirement 12):
            # A benchmark must NEVER be automatically fed into the claim calculation.
            return TreatmentCostEstimateResult(
                treatment_name=scenario.treatment_name,
                currency=currency,
                is_benchmark_matched=is_matched,
                benchmark_typical_cost=benchmark_typical,
                benchmark_cost_range=benchmark_range,
                estimated_total_cost=float(benchmark_typical) if benchmark_typical else 0.0,
                potentially_eligible_amount=0.0,
                estimated_insurer_contribution=0.0,
                estimated_patient_responsibility=0.0,
                confidence_level="Medium" if is_matched else "Insufficient evidence",
                coverage_status="not_determined",
                missing_information=["Hospital quoted treatment cost (required for claim calculation)"],
                uncertainty_notes=[
                    "Actual hospital quote not provided. In accordance with policy integrity rules, benchmark typical cost is not automatically fed into claim calculation.",
                    "Please provide an actual hospital quote to compute insurer and patient shares.",
                ],
                assumptions=[
                    "Financial calculation is Not Determined without an actual hospital quote.",
                    f"Typical benchmark cost of {benchmark_typical:,.2f} {currency} is presented for informational comparison only." if benchmark_typical else "No benchmark data available.",
                ],
                driving_factors=[],
            )

        # 3. Extract or compile policy rules
        rules = policy_rules
        if rules is None:
            rules = self._extract_rules_from_policy(policy, scenario)

        # 4. Evaluate room rent limitation if applicable
        room_penalty = 0.0
        if scenario.room_rent_daily and rules.room_rent_limit:
            if scenario.room_rent_daily > rules.room_rent_limit:
                excess_per_day = scenario.room_rent_daily - rules.room_rent_limit
                days = scenario.length_of_stay_days or (benchmark.get("length_of_stay_days", 1) if benchmark else 1)
                room_penalty = round(excess_per_day * days, 2)
                driving_factors.append(
                    DrivingFactor(
                        factor_name="Room Rent Limit Ceiling",
                        impact_amount=room_penalty,
                        description=(
                            f"Room rent of {scenario.room_rent_daily:,.2f}/day exceeds the policy cap of "
                            f"{rules.room_rent_limit:,.2f}/day. Excess for {days} day(s) ({room_penalty:,.2f}) is payable by patient."
                        ),
                    )
                )

        # 5. Non-payable items
        non_payable = float(scenario.non_payable_items or 0.0) + room_penalty
        if non_payable > 0:
            driving_factors.append(
                DrivingFactor(
                    factor_name="Non-Payable Items & Room Rent Excess",
                    impact_amount=non_payable,
                    description="Consumables, administrative charges, or room rent exceeding allowable limits.",
                )
            )

        # 6. Deterministic calculation via CalculationService (AUTHORITATIVE SINGLE ENGINE)
        calc_input = CalculationInput(
            hospital_quote=effective_cost,
            room_category=scenario.room_category,
            non_payable_items=non_payable,
            is_network_hospital=scenario.is_network_hospital,
            procedure_name=scenario.treatment_name,
            city=scenario.city,
            length_of_stay=scenario.length_of_stay_days,
            hospital_tier=scenario.hospital_type,
            patient_age=scenario.patient_age,
            pre_existing_condition=scenario.pre_existing_condition,
        )

        calc_result: CalculationResult = CalculationService.calculate(
            calc_input=calc_input,
            rules=rules,
        )

        # 7. Record financial driving factors
        if calc_result.deductible_applied > 0:
            driving_factors.append(
                DrivingFactor(
                    factor_name="Annual Policy Deductible",
                    impact_amount=calc_result.deductible_applied,
                    description=f"Annual deductible of ₹{calc_result.deductible_applied:,.2f} applied toward patient responsibility.",
                )
            )
        elif rules.deductible_status == "not_determined":
            uncertainty_notes.append(
                "Policy deductible is Not Determined in the policy schedule; treated as ₹0.00 for calculation without assuming an unstated deductible."
            )

        if calc_result.copay_applied > 0:
            pct_str = f" ({calc_result.applicable_copay_percentage:.1f}%)" if calc_result.applicable_copay_percentage else ""
            driving_factors.append(
                DrivingFactor(
                    factor_name=f"Co-payment Obligation{pct_str}",
                    impact_amount=calc_result.copay_applied,
                    description=f"Patient co-pay contribution of ₹{calc_result.copay_applied:,.2f} calculated on eligible balance.",
                )
            )
        elif scenario.is_network_hospital and (calc_result.applicable_copay_percentage == 0.0 or rules.network_copay_percentage == 0.0):
            driving_factors.append(
                DrivingFactor(
                    factor_name="Cashless Network Hospital",
                    impact_amount=0.0,
                    description="In-network cashless hospitalization: 0% co-payment applies under policy terms.",
                )
            )

        if calc_result.excess_over_limit > 0:
            driving_factors.append(
                DrivingFactor(
                    factor_name="Coverage Sub-Limit / Cap Exceeded",
                    impact_amount=calc_result.excess_over_limit,
                    description=(
                        f"Bill exceeds procedure coverage limit of ₹{calc_result.coverage_applied:,.2f}. "
                        f"Excess of ₹{calc_result.excess_over_limit:,.2f} is patient responsibility."
                    ),
                )
            )

        # Procedure-specific waiting period driving factor (from policy rule, not hardcoded)
        if rules.waiting_period_condition:
            driving_factors.append(
                DrivingFactor(
                    factor_name="Waiting Period Condition",
                    impact_amount=None,
                    description=f"Coverage is contingent upon completion of policy waiting periods ({rules.waiting_period_condition}).",
                )
            )

        if not scenario.is_network_hospital and rules.non_network_copay_percentage is not None:
            driving_factors.append(
                DrivingFactor(
                    factor_name="Out-of-Network Hospitalization",
                    impact_amount=calc_result.copay_applied if calc_result.copay_applied > 0 else None,
                    description=f"Out-of-network reimbursement: {rules.non_network_copay_percentage:.0f}% non-network co-pay applies.",
                )
            )

        # 8. Evaluate uncertainty & missing info
        confidence = "High"
        coverage_status = "covered"

        if scenario.quoted_cost is None:
            confidence = "Medium"
            missing_info.append("Specific hospital cost estimate (using benchmark typical)")

        if scenario.patient_age is None:
            missing_info.append("Patient age (affects senior citizen co-pay and waiting period thresholds)")
            if confidence == "High":
                confidence = "Medium"

        if scenario.length_of_stay_days is None and scenario.inpatient_outpatient == "inpatient":
            missing_info.append("Expected hospital length of stay")

        if not rules.has_policy_rules:
            confidence = "Low"
            coverage_status = "not_determined"
            uncertainty_notes.append("No active policy rules loaded. Calculations reflect baseline parameters.")

        assumptions.extend(calc_result.assumptions)

        return TreatmentCostEstimateResult(
            treatment_name=scenario.treatment_name,
            benchmark_treatment_id=benchmark_id,
            currency=currency,
            is_benchmark_matched=is_matched,
            benchmark_typical_cost=benchmark_typical,
            benchmark_cost_range=benchmark_range,
            estimated_total_cost=calc_result.total_treatment_cost,
            potentially_eligible_amount=calc_result.coverage_applied,
            estimated_insurer_contribution=calc_result.estimated_insurance_share,
            estimated_patient_responsibility=calc_result.estimated_patient_share,
            deductible_applied=calc_result.deductible_applied,
            deductible_status=calc_result.deductible_status,
            deductible_amount=calc_result.breakdown.get("deductible_amount"),
            policy_coverage_percentage=rules.coverage_limit_percentage_of_si,
            policy_coverage_cap=rules.absolute_cap or (rules.coverage_limit if (rules.absolute_cap is not None or rules.coverage_limit_percentage_of_si is not None) else None),
            copay_applied=calc_result.copay_applied,
            applicable_copay_percentage=calc_result.applicable_copay_percentage,
            excess_over_limit=calc_result.excess_over_limit,
            non_payable_excluded=calc_result.excluded_amount,
            room_rent_penalty=room_penalty,
            calculation_trace=calc_result.calculation_trace,
            confidence_level=confidence,
            coverage_status=coverage_status,
            driving_factors=driving_factors,
            missing_information=missing_info,
            uncertainty_notes=uncertainty_notes,
            assumptions=assumptions,
            raw_calculation=calc_result.breakdown,
        )

    def compare_what_if(
        self,
        prev_scenario: TreatmentScenarioInput,
        new_scenario: TreatmentScenarioInput,
        policy_rules: Optional[PolicyRulesInput] = None,
        policy: Optional[Policy] = None,
    ) -> WhatIfComparisonResult:
        """Demonstrate how cost estimates and patient liabilities change when additional information is supplied."""
        prev_est = self.estimate(prev_scenario, policy_rules=policy_rules, policy=policy)
        new_est = self.estimate(new_scenario, policy_rules=policy_rules, policy=policy)

        changes: List[str] = []
        explanations: List[str] = []

        # Compare input parameters
        if prev_scenario.quoted_cost != new_scenario.quoted_cost:
            old_q = prev_scenario.quoted_cost or prev_est.benchmark_typical_cost or 0
            new_q = new_scenario.quoted_cost or new_est.benchmark_typical_cost or 0
            diff_q = new_q - old_q
            changes.append(f"Hospital quote changed from ₹{old_q:,.2f} to ₹{new_q:,.2f} ({'+' if diff_q >= 0 else ''}₹{diff_q:,.2f})")

        if prev_scenario.room_category != new_scenario.room_category:
            changes.append(f"Room category changed: '{prev_scenario.room_category or 'Standard'}' → '{new_scenario.room_category or 'Standard'}'")

        if prev_scenario.patient_age != new_scenario.patient_age:
            changes.append(f"Patient age updated: {prev_scenario.patient_age or 'Not stated'} → {new_scenario.patient_age} years")

        if prev_scenario.city != new_scenario.city:
            changes.append(f"Treatment location updated: {prev_scenario.city or 'Not stated'} → {new_scenario.city}")

        if prev_scenario.is_network_hospital != new_scenario.is_network_hospital:
            changes.append(f"Provider network status updated: {'In-Network' if new_scenario.is_network_hospital else 'Out-of-Network'}")

        if prev_scenario.waiting_period_served != new_scenario.waiting_period_served:
            changes.append(f"Waiting period evidence updated: {new_scenario.waiting_period_served}")

        # Compute financial deltas from independent calculations
        cost_delta = round(new_est.estimated_total_cost - prev_est.estimated_total_cost, 2)
        ins_delta = round(new_est.estimated_insurer_contribution - prev_est.estimated_insurer_contribution, 2)
        pat_delta = round(new_est.estimated_patient_responsibility - prev_est.estimated_patient_responsibility, 2)

        if cost_delta != 0:
            if new_est.excess_over_limit > prev_est.excess_over_limit:
                excess_diff = round(new_est.excess_over_limit - prev_est.excess_over_limit, 2)
                explanations.append(
                    f"Hospital quote changed by ₹{cost_delta:+,.2f}. The quote exceeds the policy procedure sub-limit cap, causing ₹{excess_diff:+,.2f} to spill over into patient liability."
                )
            else:
                explanations.append(
                    f"Hospital quote changed by ₹{cost_delta:+,.2f}. Under policy coverage terms (within procedure sub-limit), insurer contribution changed by ₹{ins_delta:+,.2f} and patient liability by ₹{pat_delta:+,.2f}."
                )

        if prev_scenario.room_category != new_scenario.room_category:
            if new_est.room_rent_penalty > prev_est.room_rent_penalty:
                penalty_diff = round(new_est.room_rent_penalty - prev_est.room_rent_penalty, 2)
                explanations.append(
                    f"Alternative room '{new_scenario.room_category}' incurred a room rent penalty of ₹{penalty_diff:+,.2f} payable by patient."
                )
            else:
                explanations.append(
                    f"Alternative room '{new_scenario.room_category}' selected. Since no daily room rent cap is breached under policy terms, no room rent deduction applies."
                )

        if prev_scenario.is_network_hospital != new_scenario.is_network_hospital:
            if not new_scenario.is_network_hospital:
                copay_diff = round(new_est.copay_applied - prev_est.copay_applied, 2)
                explanations.append(
                    f"Out-of-network hospital selected: 10% non-network co-pay applies under policy terms (+₹{copay_diff:,.2f} to patient responsibility)."
                )
            else:
                explanations.append(
                    "In-network cashless hospital selected: 0% network co-pay applies under policy terms."
                )

        if not explanations:
            explanations.append("Parameters updated without significant impact on deterministic financial shares.")

        return WhatIfComparisonResult(
            previous_scenario=prev_scenario.model_dump(),
            updated_scenario=new_scenario.model_dump(),
            previous_estimate=prev_est,
            updated_estimate=new_est,
            changes_detected=changes,
            total_cost_delta=cost_delta,
            insurer_contribution_delta=ins_delta,
            patient_responsibility_delta=pat_delta,
            explanation_of_changes=explanations,
        )

    def _extract_rules_from_policy(
        self,
        policy: Optional[Policy],
        scenario: TreatmentScenarioInput,
    ) -> PolicyRulesInput:
        """
        Derive policy rules from the active policy's extracted metadata and clauses.
        Never fabricates arbitrary deductibles or generic co-pays.
        """
        clean_treatment = scenario.treatment_name.lower()

        if not policy:
            # When no policy is selected, do NOT fabricate 25k or 5k deductible
            return PolicyRulesInput(
                deductible=None,
                deductible_status="not_determined",
                copay_percentage=None,
                network_copay_percentage=None,
                non_network_copay_percentage=None,
                coverage_limit=None,
                room_rent_limit=None,
                room_rule_status="not_determined",
                has_policy_rules=False,
            )

        raw = getattr(policy, "raw_metadata", {}) or {}
        coins_meta = raw.get("coinsurance", {}) or {}
        ded_meta = raw.get("deductibles", {}) or {}
        limits_meta = raw.get("limits", []) or []

        # Deductible determination: only use if explicitly stated in policy metadata
        deductible_val: Optional[float] = None
        deductible_status = "not_determined"

        if ded_meta and ded_meta.get("individual_in_network") is not None:
            deductible_val = float(ded_meta["individual_in_network"])
            deductible_status = "determined"
        elif hasattr(policy, "coverage_rules") and policy.coverage_rules:
            # Check if there is an explicit contractual deductible rule (ignore legacy mock analysis rules)
            for r in policy.coverage_rules:
                if r.deductible is not None and not (r.source_reference and "Analysis #" in r.source_reference):
                    deductible_val = float(r.deductible)
                    deductible_status = "determined"
                    break

        # Co-payment determination: in-network vs out-of-network
        network_copay: Optional[float] = None
        non_network_copay: Optional[float] = None

        if raw.get("network_copay") is not None:
            network_copay = float(raw["network_copay"])
        elif coins_meta and coins_meta.get("in_network_percentage") is not None:
            network_copay = float(coins_meta["in_network_percentage"])

        if raw.get("non_network_copay") is not None:
            non_network_copay = float(raw["non_network_copay"])
        elif coins_meta and coins_meta.get("out_of_network_percentage") is not None:
            non_network_copay = float(coins_meta["out_of_network_percentage"])

        # Base Sum Insured: only if established by the policy
        sum_insured: Optional[float] = getattr(policy, "sum_insured", None)
        if sum_insured is None and raw.get("out_of_pocket_max", {}).get("individual_in_network") is not None:
            sum_insured = float(raw["out_of_pocket_max"]["individual_in_network"])
        elif sum_insured is None and hasattr(policy, "coverage_rules") and policy.coverage_rules:
            for r in policy.coverage_rules:
                ref = (r.source_reference or "").lower()
                if "extracted from" in ref or "sum insured" in ref:
                    if r.coverage_limit and r.coverage_limit >= 100000:
                        sum_insured = float(r.coverage_limit)
                        break

        # Look for procedure-specific rule in policy.coverage_rules
        matched_rule = None
        if hasattr(policy, "coverage_rules") and policy.coverage_rules:
            for r in policy.coverage_rules:
                p_name = (getattr(r, "procedure_name", None) or "").lower()
                r_name = (getattr(r, "rule_name", None) or "").lower()
                ref = (getattr(r, "source_reference", None) or "").lower()
                if p_name and (p_name in clean_treatment or clean_treatment in p_name):
                    matched_rule = r
                    break
                if r_name and (clean_treatment in r_name):
                    matched_rule = r
                    break
                if ref and (clean_treatment in ref or any(w in ref for w in clean_treatment.split() if len(w) > 3)):
                    matched_rule = r
                    break
            # Fallback if policy has a general rule (only if rule has no specific procedure or is explicitly general)
            if not matched_rule and len(policy.coverage_rules) == 1:
                r0 = policy.coverage_rules[0]
                r0_proc = (getattr(r0, "procedure_name", None) or "").strip().lower()
                if not r0_proc or r0_proc in ("general", "all", "inpatient", "hospitalization", "basic"):
                    matched_rule = r0

        cov_limit: Optional[float] = None
        cov_pct_of_si: Optional[float] = None
        abs_cap: Optional[float] = None
        waiting_dur: Optional[int] = None
        waiting_cond: Optional[str] = None
        cov_status = "covered"

        # Also check limits_meta from extracted document
        matched_lim = None
        for lim in limits_meta:
            cat = (lim.get("service_or_category") or lim.get("procedure") or lim.get("name") or "").lower()
            if cat and (cat in clean_treatment or clean_treatment in cat or any(w in clean_treatment for w in cat.split() if len(w) > 3)):
                matched_lim = lim
                break

        if matched_lim:
            if matched_lim.get("percentage_of_sum_insured") is not None:
                cov_pct_of_si = float(matched_lim["percentage_of_sum_insured"])
            elif matched_lim.get("percentage_of_si") is not None:
                cov_pct_of_si = float(matched_lim["percentage_of_si"])

            if matched_lim.get("absolute_max") is not None:
                abs_cap = float(matched_lim["absolute_max"])
            elif matched_lim.get("limit_value") is not None:
                try:
                    abs_cap = float(str(matched_lim["limit_value"]).replace(",", ""))
                except ValueError:
                    pass

            if matched_lim.get("waiting_period"):
                waiting_cond = str(matched_lim["waiting_period"])
                m_w = re.search(r"([0-9]+)\s*(?:month|year)", waiting_cond, re.IGNORECASE)
                if m_w:
                    waiting_dur = int(m_w.group(1))

        if matched_rule:
            rule_pct = getattr(matched_rule, "coverage_limit_percentage_of_si", None) or matched_rule.coverage_percentage
            if rule_pct is not None:
                cov_pct_of_si = rule_pct
            rule_cap = getattr(matched_rule, "coverage_limit_amount", None) or matched_rule.coverage_limit
            if rule_cap is not None:
                abs_cap = rule_cap
            cov_status = matched_rule.coverage_status or "covered"
            if matched_rule.waiting_period:
                waiting_cond = matched_rule.waiting_period
                m_w = re.search(r"([0-9]+)\s*(?:month|year)", matched_rule.waiting_period, re.IGNORECASE)
                if m_w:
                    waiting_dur = int(m_w.group(1))

            if matched_rule.copay_percentage is not None and network_copay is None:
                network_copay = matched_rule.copay_percentage

        if cov_pct_of_si is not None and sum_insured:
            calc_lim = round(sum_insured * (cov_pct_of_si / 100.0), 2)
            cov_limit = min(calc_lim, abs_cap) if abs_cap else calc_lim
        else:
            cov_limit = abs_cap or sum_insured

        if not matched_rule and not matched_lim:
            cov_status = "not_determined" if sum_insured is None else "covered"
            cov_limit = sum_insured

        # Room rent rule: only if policy explicitly establishes a room rent rule
        room_rent_limit: Optional[float] = None
        room_rule_status = "not_determined"

        return PolicyRulesInput(
            deductible=deductible_val,
            deductible_status=deductible_status,
            copay_fixed=0.0,
            copay_percentage=None,
            network_copay_percentage=network_copay,
            non_network_copay_percentage=non_network_copay,
            coverage_limit=cov_limit,
            coverage_limit_percentage_of_si=cov_pct_of_si,
            absolute_cap=abs_cap,
            sum_insured=sum_insured,
            coverage_status=cov_status,
            room_rent_limit=room_rent_limit,
            room_rule_status=room_rule_status,
            waiting_period_duration=waiting_dur,
            waiting_period_condition=waiting_cond,
            waiting_period_status="determined" if waiting_dur else "not_determined",
            has_policy_rules=True,
            source_type="contractual_rule",
        )


# Default singleton instance
default_treatment_estimation_service = TreatmentCostEstimationService()


def get_treatment_estimation_service() -> TreatmentCostEstimationService:
    return default_treatment_estimation_service
