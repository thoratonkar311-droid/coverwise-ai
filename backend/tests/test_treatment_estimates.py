import pytest
from fastapi.testclient import TestClient

from app.models.policy import Policy
from app.models.coverage_rule import CoverageRule
from app.db.session import SessionLocal


@pytest.fixture
def policy_with_rules() -> int:
    """Create a policy with explicit deductible, copay, sub-limit, and room rent cap."""
    db = SessionLocal()
    try:
        policy = Policy(
            filename="comprehensive_health_policy.pdf",
            policy_number="CMP-2026-TEST-777",
            insurer_name="Care Premier Assurance",
            plan_name="Care Premier Gold",
            status="analyzed",
        )
        db.add(policy)
        db.commit()
        db.refresh(policy)

        rule = CoverageRule(
            policy_id=policy.id,
            coverage_status="covered",
            deductible=20000.0,
            copay_percentage=10.0,
            coverage_limit=250000.0,  # 2.5 Lakh sub-limit
            room_category="Single Private",
            source_reference="Section 2.1 Benefit Schedule",
        )
        db.add(rule)
        db.commit()
        return policy.id
    finally:
        db.close()


def test_estimate_treatment_cost_with_quote(client: TestClient, policy_with_rules: int) -> None:
    """Verify deterministic estimation combining policy rules, scenario, and quote."""
    payload = {
        "policy_id": policy_with_rules,
        "scenario": {
            "treatment_name": "Total Knee Replacement",
            "quoted_cost": 280000.0,
            "patient_age": 55,
            "city": "Mumbai",
            "is_network_hospital": True,
        },
    }
    res = client.post("/api/treatment-estimates", json=payload)
    assert res.status_code == 200
    data = res.json()

    assert data["estimated_total_cost"] == 280000.0
    # Sub-limit of 250,000 applies -> 30,000 excess to patient
    assert data["potentially_eligible_amount"] == 250000.0
    assert data["excess_over_limit"] == 30000.0
    # Deductible of 20,000 applied on 250,000 -> 230,000
    assert data["deductible_applied"] == 20000.0
    # 10% copay on 230,000 -> 23,000
    assert data["copay_applied"] == 23000.0
    # Insurer share = 230,000 - 23,000 = 207,000
    assert data["estimated_insurer_contribution"] == 207000.0
    # Patient share = 280,000 - 207,000 = 73,000 (Deductible 20k + Copay 23k + Excess 30k)
    assert data["estimated_patient_responsibility"] == 73000.0
    assert round(data["estimated_insurer_contribution"] + data["estimated_patient_responsibility"], 2) == 280000.0

    # Verify driving factors
    factor_names = [f["factor_name"] for f in data["driving_factors"]]
    assert any("Deductible" in fn for fn in factor_names)
    assert any("Co-payment" in fn for fn in factor_names)
    assert any("Sub-Limit" in fn for fn in factor_names)
    assert "not insurer authorization" in data["disclaimer"].lower()


def test_estimate_benchmark_fallback_when_no_quote(client: TestClient) -> None:
    """Verify fallback to synthetic benchmark typical cost when user provides no quote."""
    payload = {
        "scenario": {
            "treatment_name": "cataract surgery",
        },
    }
    res = client.post("/api/treatment-estimates", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["is_benchmark_matched"] is True
    assert data["estimated_total_cost"] > 0
    assert data["benchmark_typical_cost"] == 45000.0
    assert data["confidence_level"] in ("Low", "Medium", "High")


def test_estimate_abstention_on_unknown_procedure(client: TestClient) -> None:
    """Verify system abstains when procedure is unknown and no quote is supplied."""
    payload = {
        "scenario": {
            "treatment_name": "obscure_unrecognized_treatment_xyz",
        },
    }
    res = client.post("/api/treatment-estimates", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["confidence_level"] == "Insufficient evidence"
    assert data["coverage_status"] == "not_determined"
    assert data["estimated_total_cost"] == 0.0
    assert len(data["missing_information"]) > 0


def test_what_if_comparison_analysis(client: TestClient, policy_with_rules: int) -> None:
    """Verify What-If analysis comparing two scenario states."""
    payload = {
        "policy_id": policy_with_rules,
        "previous_scenario": {
            "treatment_name": "Knee replacement",
            "quoted_cost": 250000.0,
            "patient_age": None,
        },
        "updated_scenario": {
            "treatment_name": "Knee replacement",
            "quoted_cost": 350000.0,
            "patient_age": 62,
        },
    }
    res = client.post("/api/treatment-estimates/what-if", json=payload)
    assert res.status_code == 200
    data = res.json()

    assert data["total_cost_delta"] == 100000.0
    assert len(data["changes_detected"]) >= 2
    assert len(data["explanation_of_changes"]) > 0
    # Because 250k was already the cap, the entire 100k increase goes to patient
    assert data["patient_responsibility_delta"] == 100000.0
    assert data["insurer_contribution_delta"] == 0.0


def test_get_benchmark_treatments_catalog(client: TestClient) -> None:
    """Verify GET /api/treatment-estimates/benchmarks returns synthetic benchmark catalog."""
    res = client.get("/api/treatment-estimates/benchmarks")
    assert res.status_code == 200
    data = res.json()
    assert data["data_source_type"] == "synthetic_demo_data"
    assert data["total_treatments"] >= 10
    treatments = data["treatments"]
    names = [t["treatment_name"].lower() for t in treatments]
    assert any("knee" in n for n in names)
    assert any("cataract" in n for n in names)
    assert any("angioplasty" in n for n in names)
    assert any("appendectomy" in n for n in names)
    assert any("hernia" in n for n in names)
    assert any("maternity" in n for n in names)
    assert any("dialysis" in n for n in names)
    assert any("chemotherapy" in n for n in names)
    assert any("icu" in n for n in names)
