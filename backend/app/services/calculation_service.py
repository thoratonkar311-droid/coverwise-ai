from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class CalculationInput:
    """Raw financial and clinical inputs for treatment simulation."""

    hospital_quote: float
    room_category: Optional[str] = None
    non_payable_items: Optional[float] = None
    is_network_hospital: bool = True
    procedure_name: Optional[str] = None
    city: Optional[str] = None
    length_of_stay: Optional[int] = None
    hospital_tier: Optional[str] = None
    patient_age: Optional[int] = None
    pre_existing_condition: bool = False


@dataclass(frozen=True)
class PolicyRulesInput:
    """Coverage parameters extracted from contractual policy rules."""

    deductible: Optional[float] = None
    deductible_status: str = "determined"  # "determined" or "not_determined"
    copay_fixed: Optional[float] = None
    copay_percentage: Optional[float] = None
    network_copay_percentage: Optional[float] = None
    non_network_copay_percentage: Optional[float] = None
    coverage_limit: Optional[float] = None
    coverage_limit_percentage_of_si: Optional[float] = None
    absolute_cap: Optional[float] = None
    sum_insured: Optional[float] = None
    coverage_status: str = "covered"
    room_rent_limit: Optional[float] = None
    room_rule_status: str = "not_determined"  # "determined" or "not_determined"
    waiting_period_duration: Optional[int] = None
    waiting_period_condition: Optional[str] = None
    waiting_period_status: str = "determined"
    has_policy_rules: bool = True
    source_type: str = "contractual_rule"
    evidence: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class CalculationResult:
    """Deterministic calculation outcome with granular financial breakdown and audit trace."""

    total_treatment_cost: float
    estimated_insurance_share: float
    estimated_patient_share: float
    deductible_applied: float
    copay_applied: float
    coverage_applied: float
    excluded_amount: float
    excess_over_limit: float
    deductible_status: str = "determined"
    applicable_copay_percentage: Optional[float] = None
    is_network_hospital: bool = True
    calculation_trace: List[str] = field(default_factory=list)
    assumptions: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    breakdown: Dict[str, Any] = field(default_factory=dict)
    is_conditional_on_deductible: bool = False
    policy_coverage_percentage: Optional[float] = None
    policy_coverage_cap: Optional[float] = None


class CalculationService:
    """
    Deterministic treatment cost calculation service.

    Given the exact same input and policy rules, it always returns identical results.
    Authoritative single source of truth for financial math across all modules.
    No LLM arithmetic is permitted.
    """

    @staticmethod
    def calculate(
        calc_input: CalculationInput,
        rules: PolicyRulesInput,
    ) -> CalculationResult:
        """
        Execute deterministic out-of-pocket cost simulation.

        Formula:
        1. Quote = hospital_quote
        2. Ineligible = non_payable_items
        3. Eligible bill = Quote - Ineligible
        4. Sub-limit cap = min(Eligible bill, coverage_limit / cap) -> Excess to patient
        5. Deductible applied = min(Capped eligible, deductible) (if determined)
        6. Remaining after deductible = Capped eligible - Deductible
        7. Copay applied = Applicable network/non-network co-pay on remaining + Fixed copay
        8. Insurer Share = Remaining after deductible - Copay applied
        9. Patient Share = Quote - Insurer Share
        """
        # Validate inputs
        if calc_input.hospital_quote <= 0:
            raise ValueError("hospital_quote must be greater than zero.")

        quote = round(float(calc_input.hospital_quote), 2)
        non_payable = round(float(calc_input.non_payable_items or 0.0), 2)

        trace: List[str] = []
        trace.append(f"Step 1: Hospital Quote = ₹{quote:,.2f}")

        assumptions: List[str] = [
            f"Calculation reflects {'in-network cashless' if calc_input.is_network_hospital else 'out-of-network reimbursement'} hospital setting.",
            "Standard non-medical expenses (administrative charges, disposable PPE, hygiene packs) are non-payable.",
            "Assumes policy is in active status with no premium default.",
        ]
        warnings: List[str] = []

        if not rules.has_policy_rules:
            warnings.append(
                "No specific policy rules found. Using baseline parameters; actual insurance settlement may differ."
            )

        # 1. Non-payable exclusion
        eligible_amount = max(0.0, round(quote - non_payable, 2))
        trace.append(
            f"Step 2: Non-payable items deduction = ₹{non_payable:,.2f} -> Eligible amount = ₹{eligible_amount:,.2f}"
        )

        # 2. Coverage Limit / Sub-limit capping
        # Evaluate percentage of sum insured cap (e.g. 60% of SI max ₹600,000 for TKR)
        effective_limit: Optional[float] = None
        if rules.coverage_limit_percentage_of_si is not None and rules.sum_insured is not None:
            pct_limit = round(rules.sum_insured * (rules.coverage_limit_percentage_of_si / 100.0), 2)
            if rules.absolute_cap is not None:
                effective_limit = min(pct_limit, round(float(rules.absolute_cap), 2))
                trace.append(
                    f"Step 3: Procedure sub-limit cap evaluated: {rules.coverage_limit_percentage_of_si:.0f}% of Sum Insured (₹{rules.sum_insured:,.2f}) = ₹{pct_limit:,.2f}, capped at absolute limit ₹{rules.absolute_cap:,.2f} -> Effective limit = ₹{effective_limit:,.2f}"
                )
            else:
                effective_limit = pct_limit
                trace.append(
                    f"Step 3: Procedure sub-limit cap evaluated: {rules.coverage_limit_percentage_of_si:.0f}% of Sum Insured = ₹{effective_limit:,.2f}"
                )
        elif rules.coverage_limit is not None and rules.coverage_limit >= 0:
            effective_limit = round(float(rules.coverage_limit), 2)
            trace.append(f"Step 3: Procedure coverage limit applied = ₹{effective_limit:,.2f}")
        elif rules.absolute_cap is not None and rules.absolute_cap >= 0:
            effective_limit = round(float(rules.absolute_cap), 2)
            trace.append(f"Step 3: Procedure absolute cap applied = ₹{effective_limit:,.2f}")
        else:
            trace.append("Step 3: No procedure-specific sub-limit cap; subject to overall annual sum insured.")

        if effective_limit is not None:
            if eligible_amount > effective_limit:
                excess_over_limit = round(eligible_amount - effective_limit, 2)
                capped_eligible = effective_limit
                warnings.append(
                    f"Hospital quote exceeds the coverage limit of ₹{effective_limit:,.2f}. Excess of ₹{excess_over_limit:,.2f} is payable by patient."
                )
                trace.append(
                    f"Step 4: Eligible amount ₹{eligible_amount:,.2f} exceeds limit ₹{effective_limit:,.2f} -> Capped eligible = ₹{capped_eligible:,.2f}, Excess to patient = ₹{excess_over_limit:,.2f}"
                )
            else:
                excess_over_limit = 0.0
                capped_eligible = eligible_amount
                trace.append(
                    f"Step 4: Eligible amount ₹{eligible_amount:,.2f} is within limit ₹{effective_limit:,.2f} -> Capped eligible = ₹{capped_eligible:,.2f}, Excess = ₹0.00"
                )
        else:
            excess_over_limit = 0.0
            capped_eligible = eligible_amount
            if rules.has_policy_rules:
                assumptions.append("No explicit procedure sub-limit specified; subject to overall annual sum insured.")
            trace.append(f"Step 4: Capped eligible amount = ₹{capped_eligible:,.2f}")

        # 3. Deductible application
        is_conditional_on_deductible = False
        deductible_status = rules.deductible_status
        if rules.deductible is not None:
            deductible_val = round(float(rules.deductible), 2)
            deductible_applied = min(capped_eligible, deductible_val)
            deductible_status = "determined"
            if deductible_applied > 0:
                warnings.append(
                    f"Policy deductible of ₹{deductible_applied:,.2f} applied toward patient responsibility."
                )
            trace.append(
                f"Step 5: Policy deductible of ₹{deductible_val:,.2f} applied -> Deductible applied = ₹{deductible_applied:,.2f}"
            )
        else:
            deductible_val = 0.0
            deductible_applied = 0.0
            deductible_status = "not_determined"
            is_conditional_on_deductible = True
            assumptions.append(
                "Policy deductible is Not Determined in policy terms. Financial estimate is conditional on ₹0 deductible being applied upon claim adjudication."
            )
            warnings.append(
                "Policy deductible is Not Determined; financial breakdown is conditional on ₹0 deductible."
            )
            trace.append(
                "Step 5: Policy deductible is Not Determined in policy terms. Calculation proceeds conditionally assuming ₹0 deductible."
            )

        after_deductible = round(capped_eligible - deductible_applied, 2)
        trace.append(f"Step 6: Eligible balance after deductible = ₹{after_deductible:,.2f}")

        # 4. Co-payment application (Network vs Non-Network)
        applicable_copay_pct: Optional[float] = None
        if calc_input.is_network_hospital:
            if rules.network_copay_percentage is not None:
                applicable_copay_pct = float(rules.network_copay_percentage)
            elif rules.copay_percentage is not None:
                applicable_copay_pct = float(rules.copay_percentage)
            else:
                applicable_copay_pct = 0.0
            trace.append(
                f"Step 7: Cashless Network Hospital = True -> In-network co-pay of {applicable_copay_pct:.1f}% applied."
            )
        else:
            if rules.non_network_copay_percentage is not None:
                applicable_copay_pct = float(rules.non_network_copay_percentage)
            elif rules.copay_percentage is not None:
                applicable_copay_pct = float(rules.copay_percentage)
            else:
                applicable_copay_pct = 0.0
            trace.append(
                f"Step 7: Cashless Network Hospital = False -> Out-of-network co-pay of {applicable_copay_pct:.1f}% applied."
            )

        copay_applied = 0.0
        if applicable_copay_pct > 0:
            if applicable_copay_pct > 100.0:
                raise ValueError("copay_percentage cannot exceed 100%.")
            copay_from_pct = round(after_deductible * (applicable_copay_pct / 100.0), 2)
            copay_applied = round(copay_applied + copay_from_pct, 2)
            warnings.append(
                f"Co-payment of {applicable_copay_pct:.1f}% (₹{copay_from_pct:,.2f}) applied on eligible claim balance."
            )
            trace.append(
                f"Step 8: Co-pay calculation: {applicable_copay_pct:.1f}% of ₹{after_deductible:,.2f} = ₹{copay_from_pct:,.2f}"
            )
        else:
            trace.append("Step 8: Co-pay percentage is 0.0% -> ₹0.00 co-payment.")

        copay_fixed = round(float(rules.copay_fixed or 0.0), 2) if rules.copay_fixed else 0.0
        if copay_fixed > 0:
            remaining_room = max(0.0, after_deductible - copay_applied)
            fixed_applied = min(remaining_room, copay_fixed)
            copay_applied = round(copay_applied + fixed_applied, 2)
            warnings.append(
                f"Fixed co-payment of ₹{fixed_applied:,.2f} applied toward patient share."
            )
            trace.append(f"Step 8b: Fixed co-payment ₹{fixed_applied:,.2f} applied.")

        # 5. Final shares calculation
        insurer_share = max(0.0, round(after_deductible - copay_applied, 2))
        patient_share = max(0.0, round(quote - insurer_share, 2))

        trace.append(
            f"Step 9: Insurer Share = ₹{after_deductible:,.2f} - ₹{copay_applied:,.2f} = ₹{insurer_share:,.2f}"
        )
        trace.append(
            f"Step 10: Patient Share = Quote (₹{quote:,.2f}) - Insurer Share (₹{insurer_share:,.2f}) = ₹{patient_share:,.2f}"
        )

        # Precision invariant check
        assert round(insurer_share + patient_share, 2) == quote, (
            f"Financial reconciliation error: {insurer_share} + {patient_share} != {quote}"
        )

        breakdown = {
            "hospital_quote": quote,
            "non_payable_deduction": non_payable,
            "eligible_amount": eligible_amount,
            "coverage_limit": effective_limit,
            "excess_over_limit": excess_over_limit,
            "capped_eligible_amount": capped_eligible,
            "deductible_amount": deductible_val if rules.deductible is not None else None,
            "deductible_applied": deductible_applied,
            "deductible_status": deductible_status,
            "is_conditional_on_deductible": is_conditional_on_deductible,
            "policy_coverage_percentage": rules.coverage_limit_percentage_of_si,
            "policy_coverage_cap": rules.absolute_cap or rules.coverage_limit,
            "after_deductible": after_deductible,
            "copay_percentage": applicable_copay_pct,
            "is_network_hospital": calc_input.is_network_hospital,
            "copay_applied": copay_applied,
            "estimated_insurance_share": insurer_share,
            "estimated_patient_share": patient_share,
            "calculation_trace": trace,
        }

        return CalculationResult(
            total_treatment_cost=quote,
            estimated_insurance_share=insurer_share,
            estimated_patient_share=patient_share,
            deductible_applied=deductible_applied,
            copay_applied=copay_applied,
            coverage_applied=capped_eligible,
            excluded_amount=round(non_payable + excess_over_limit, 2),
            excess_over_limit=excess_over_limit,
            deductible_status=deductible_status,
            applicable_copay_percentage=applicable_copay_pct,
            is_network_hospital=calc_input.is_network_hospital,
            calculation_trace=trace,
            assumptions=assumptions,
            warnings=warnings,
            breakdown=breakdown,
            is_conditional_on_deductible=is_conditional_on_deductible,
            policy_coverage_percentage=rules.coverage_limit_percentage_of_si,
            policy_coverage_cap=rules.absolute_cap or rules.coverage_limit,
        )

