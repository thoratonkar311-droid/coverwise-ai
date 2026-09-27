import pytest

from app.services.calculation_service import (
    CalculationInput,
    CalculationResult,
    CalculationService,
    PolicyRulesInput,
)


def test_deterministic_calculation_consistency() -> None:
    """Verify identical inputs yield 100% deterministic identical outputs across repeated executions."""
    calc_input = CalculationInput(hospital_quote=175000.0, room_category="Private Single")
    rules = PolicyRulesInput(
        deductible=5000.0,
        copay_percentage=10.0,
        coverage_limit=150000.0,
        has_policy_rules=True,
    )

    baseline = CalculationService.calculate(calc_input, rules)

    for _ in range(50):
        result = CalculationService.calculate(calc_input, rules)
        assert result.estimated_insurance_share == baseline.estimated_insurance_share
        assert result.estimated_patient_share == baseline.estimated_patient_share
        assert result.deductible_applied == baseline.deductible_applied
        assert result.copay_applied == baseline.copay_applied
        assert result.coverage_applied == baseline.coverage_applied
        assert result.excluded_amount == baseline.excluded_amount


def test_calculation_financial_reconciliation_invariant() -> None:
    """Verify that insurance share + patient share strictly equals total cost without paisa leakage."""
    test_quotes = [100.0, 49999.99, 150000.0, 321456.78, 1000000.0]
    for quote in test_quotes:
        calc_input = CalculationInput(hospital_quote=quote, non_payable_items=2500.0)
        rules = PolicyRulesInput(
            deductible=1500.0,
            copay_percentage=12.5,
            copay_fixed=500.0,
            coverage_limit=quote * 0.8,
            has_policy_rules=True,
        )
        res = CalculationService.calculate(calc_input, rules)
        total_reconciled = round(res.estimated_insurance_share + res.estimated_patient_share, 2)
        assert total_reconciled == round(quote, 2)


def test_calculation_sublimit_capping_scenario() -> None:
    """
    Scenario: Cataract Procedure with ₹40,000 sublimit cap.
    Quote: ₹65,000.
    Excess: ₹25,000 to patient.
    """
    calc_input = CalculationInput(hospital_quote=65000.0)
    rules = PolicyRulesInput(
        coverage_limit=40000.0,
        deductible=0.0,
        copay_percentage=0.0,
        has_policy_rules=True,
    )
    res = CalculationService.calculate(calc_input, rules)
    assert res.coverage_applied == 40000.0
    assert res.excess_over_limit == 25000.0
    assert res.estimated_insurance_share == 40000.0
    assert res.estimated_patient_share == 25000.0
    assert any("exceeds the coverage limit" in w for w in res.warnings)


def test_calculation_copay_and_deductible_scenario() -> None:
    """
    Scenario: Knee Replacement.
    Quote: ₹200,000.
    Deductible: ₹10,000.
    Remaining: ₹190,000.
    Copay 10%: ₹19,000.
    Insurer: ₹171,000.
    Patient: ₹29,000 (10k deductible + 19k copay).
    """
    calc_input = CalculationInput(hospital_quote=200000.0)
    rules = PolicyRulesInput(
        deductible=10000.0,
        copay_percentage=10.0,
        coverage_limit=300000.0,
        has_policy_rules=True,
    )
    res = CalculationService.calculate(calc_input, rules)
    assert res.deductible_applied == 10000.0
    assert res.copay_applied == 19000.0
    assert res.estimated_insurance_share == 171000.0
    assert res.estimated_patient_share == 29000.0


def test_calculation_missing_policy_rules_warning() -> None:
    """
    Rule: Never silently invent missing policy rules.
    When rules are unavailable, emit explicit warning indicating baseline parameters.
    """
    calc_input = CalculationInput(hospital_quote=120000.0)
    rules = PolicyRulesInput(
        has_policy_rules=False,
    )
    res = CalculationService.calculate(calc_input, rules)
    assert any("No specific policy rules found" in w for w in res.warnings)
    # Entire amount not covered or covered under default baseline without invented sublimits
    assert res.excess_over_limit == 0.0


def test_calculation_invalid_inputs_raise_errors() -> None:
    """Verify invalid inputs raise ValueError immediately."""
    rules = PolicyRulesInput()

    # Zero or negative quote
    with pytest.raises(ValueError, match="greater than zero"):
        CalculationService.calculate(CalculationInput(hospital_quote=0.0), rules)

    with pytest.raises(ValueError, match="greater than zero"):
        CalculationService.calculate(CalculationInput(hospital_quote=-500.0), rules)

    # Copay percentage > 100
    with pytest.raises(ValueError, match="cannot exceed 100%"):
        CalculationService.calculate(
            CalculationInput(hospital_quote=50000.0),
            PolicyRulesInput(copay_percentage=120.0),
        )
