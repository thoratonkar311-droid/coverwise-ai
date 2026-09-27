from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class CalculationInput:
    """Raw financial inputs for treatment simulation."""

    hospital_quote: float
    room_category: Optional[str] = None
    non_payable_items: Optional[float] = None


@dataclass(frozen=True)
class PolicyRulesInput:
    """Coverage parameters extracted from policy or supplied via user override."""

    deductible: Optional[float] = None
    copay_fixed: Optional[float] = None
    copay_percentage: Optional[float] = None
    coverage_limit: Optional[float] = None
    room_rent_limit: Optional[float] = None
    has_policy_rules: bool = True


@dataclass
class CalculationResult:
    """Deterministic calculation outcome with granular financial breakdown."""

    total_treatment_cost: float
    estimated_insurance_share: float
    estimated_patient_share: float
    deductible_applied: float
    copay_applied: float
    coverage_applied: float
    excluded_amount: float
    excess_over_limit: float
    assumptions: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    breakdown: Dict[str, Any] = field(default_factory=dict)


class CalculationService:
    """
    Deterministic treatment cost calculation service.

    Given the exact same input and policy rules, it always returns identical results.
    Clearly separates Input, Policy Rules, Calculation, and Result.
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
        4. Sub-limit cap = min(Eligible bill, coverage_limit) -> Excess to patient
        5. Deductible applied = min(Capped eligible, deductible)
        6. Remaining after deductible = Capped eligible - Deductible
        7. Copay applied = Copay percentage on remaining + Fixed copay
        8. Insurer Share = Remaining after deductible - Copay applied
        9. Patient Share = Quote - Insurer Share
        """
        # Validate inputs
        if calc_input.hospital_quote <= 0:
            raise ValueError("hospital_quote must be greater than zero.")

        quote = round(float(calc_input.hospital_quote), 2)
        non_payable = round(float(calc_input.non_payable_items or 0.0), 2)

        assumptions: List[str] = [
            "Calculation assumes treatment is conducted at an authorized in-network hospital.",
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

        # 2. Coverage Limit / Sub-limit capping
        if rules.coverage_limit is not None and rules.coverage_limit >= 0:
            cov_limit = round(float(rules.coverage_limit), 2)
            if eligible_amount > cov_limit:
                excess_over_limit = round(eligible_amount - cov_limit, 2)
                capped_eligible = cov_limit
                warnings.append(
                    f"Hospital quote exceeds the coverage limit of {cov_limit:,.2f}. Excess of {excess_over_limit:,.2f} is payable by patient."
                )
            else:
                excess_over_limit = 0.0
                capped_eligible = eligible_amount
        else:
            excess_over_limit = 0.0
            capped_eligible = eligible_amount
            if rules.has_policy_rules:
                assumptions.append("No explicit procedure sub-limit specified; subject to overall annual sum insured.")

        # 3. Deductible application
        deductible_val = round(float(rules.deductible or 0.0), 2) if rules.deductible else 0.0
        deductible_applied = min(capped_eligible, deductible_val)
        after_deductible = round(capped_eligible - deductible_applied, 2)

        if deductible_applied > 0:
            warnings.append(
                f"Policy deductible of {deductible_applied:,.2f} applied toward patient responsibility."
            )

        # 4. Co-payment application
        copay_applied = 0.0
        copay_pct = float(rules.copay_percentage or 0.0) if rules.copay_percentage else 0.0
        if copay_pct > 0:
            if copay_pct > 100.0:
                raise ValueError("copay_percentage cannot exceed 100%.")
            copay_from_pct = round(after_deductible * (copay_pct / 100.0), 2)
            copay_applied = round(copay_applied + copay_from_pct, 2)
            warnings.append(
                f"Co-payment of {copay_pct:.1f}% ({copay_from_pct:,.2f}) applied on eligible claim balance."
            )

        copay_fixed = round(float(rules.copay_fixed or 0.0), 2) if rules.copay_fixed else 0.0
        if copay_fixed > 0:
            remaining_room = max(0.0, after_deductible - copay_applied)
            fixed_applied = min(remaining_room, copay_fixed)
            copay_applied = round(copay_applied + fixed_applied, 2)
            warnings.append(
                f"Fixed co-payment of {fixed_applied:,.2f} applied toward patient share."
            )

        # 5. Final shares calculation
        insurer_share = max(0.0, round(after_deductible - (copay_applied if copay_pct > 0 or copay_fixed > 0 else 0.0), 2))
        patient_share = max(0.0, round(quote - insurer_share, 2))

        # Precision invariant check
        assert round(insurer_share + patient_share, 2) == quote, (
            f"Financial reconciliation error: {insurer_share} + {patient_share} != {quote}"
        )

        breakdown = {
            "hospital_quote": quote,
            "non_payable_deduction": non_payable,
            "eligible_amount": eligible_amount,
            "coverage_limit": rules.coverage_limit,
            "excess_over_limit": excess_over_limit,
            "capped_eligible_amount": capped_eligible,
            "deductible_amount": deductible_val,
            "deductible_applied": deductible_applied,
            "after_deductible": after_deductible,
            "copay_percentage": copay_pct if copay_pct > 0 else None,
            "copay_applied": copay_applied,
            "estimated_insurance_share": insurer_share,
            "estimated_patient_share": patient_share,
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
            assumptions=assumptions,
            warnings=warnings,
            breakdown=breakdown,
        )
