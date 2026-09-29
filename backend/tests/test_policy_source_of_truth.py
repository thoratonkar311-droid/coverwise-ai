"""
Regression test suite verifying uploaded health insurance policy as the authoritative source of truth.
Covers the 10 mandatory regression tests specified in CoverWise AI architecture prompt.
"""

import pytest
from fastapi.testclient import TestClient

from app.models.policy import Policy
from app.models.coverage_rule import CoverageRule
from app.db.session import SessionLocal


def _create_user_and_token(client: TestClient, email: str, name: str) -> str:
    """Helper to register a user and return the JWT bearer token."""
    res = client.post(
        "/api/auth/register",
        json={"email": email, "password": "SecurePassword123!", "full_name": name},
    )
    assert res.status_code == 201
    return res.json()["access_token"]


@pytest.fixture
def synthetic_tkr_policy() -> int:
    """
    Create synthetic test policy corresponding to CoverWise_Synthetic_Health_Policy_Test.pdf:
    - Sum Insured: 10 Lakh (₹1,000,000)
    - Deductible: Not specified (Not Determined)
    - Network co-pay: 0%
    - Non-network co-pay: 10%
    - TKR: Covered up to 60% of sum insured (max ₹600,000)
    - Waiting period: 36 months if degenerative; accident rule if accident-related
    """
    db = SessionLocal()
    try:
        policy = Policy(
            filename="CoverWise_Synthetic_Health_Policy_Test.pdf",
            policy_number="CW-SYN-2026-TKR",
            insurer_name="CoverWise National Assurance",
            plan_name="Comprehensive Health Shield Gold",
            status="analyzed",
            raw_metadata={
                "extracted_metadata": {
                    "policy_id": "CW-SYN-2026-TKR",
                    "policy_name": "Comprehensive Health Shield Gold",
                    "insurer_name": "CoverWise National Assurance",
                },
                "out_of_pocket_max": {
                    "individual_in_network": 1000000.0,
                },
                "network_copay": 0.0,
                "non_network_copay": 10.0,
                "limits": [
                    {
                        "procedure": "Total Knee Replacement",
                        "percentage_of_sum_insured": 60.0,
                        "absolute_max": 600000.0,
                        "waiting_period": "36 months if degenerative; accident rule applies for accident-related",
                    }
                ],
            },
        )
        db.add(policy)
        db.commit()
        db.refresh(policy)

        # Coverage rule for TKR with 0% network copay, deductible not determined
        rule = CoverageRule(
            policy_id=policy.id,
            coverage_status="covered",
            deductible=None,
            copay_percentage=0.0,
            coverage_limit=600000.0,
            waiting_period="36 months if degenerative; accident rule applies for accident-related",
            room_category="Single Private Room",
            source_reference="Section 4.2 Orthopedic Procedures (Page 7)",
        )
        db.add(rule)
        db.commit()
        return policy.id
    finally:
        db.close()


# TEST 1: Network TKR - quote ₹250,000, network = true
def test_regression_test_1_network_tkr(client: TestClient, synthetic_tkr_policy: int) -> None:
    """Verify that for Cashless Network hospitalization, non-network 10% co-pay is NOT applied."""
    payload = {
        "policy_id": synthetic_tkr_policy,
        "scenario": {
            "treatment_name": "Total Knee Replacement",
            "quoted_cost": 250000.0,
            "patient_age": 54,
            "city": "Mumbai",
            "room_category": "Single Private Room",
            "length_of_stay": 4,
            "is_network_hospital": True,
            "pre_existing_condition": False,
        },
    }
    res = client.post("/api/treatment-estimates", json=payload)
    assert res.status_code == 200
    data = res.json()

    # Network co-pay is 0%, no deductible
    assert data["copay_applied"] == 0.0
    assert data["applicable_copay_percentage"] == 0.0
    assert data["deductible_applied"] == 0.0
    assert data["deductible_status"] == "not_determined"
    assert data["estimated_total_cost"] == 250000.0
    assert data["potentially_eligible_amount"] == 250000.0
    assert data["estimated_insurer_contribution"] == 250000.0
    assert data["estimated_patient_responsibility"] == 0.0

    # Verification of trace steps
    trace = data.get("calculation_trace", [])
    assert any("Cashless Network Hospital = True -> In-network co-pay of 0.0% applied" in step for step in trace)
    assert any("Co-pay percentage is 0.0% -> ₹0.00 co-payment" in step for step in trace)
    assert any("deductible is Not Determined" in step for step in trace)


# TEST 2: Non-network TKR - quote ₹250,000, network = false
def test_regression_test_2_non_network_tkr(client: TestClient, synthetic_tkr_policy: int) -> None:
    """Verify that when network = false, policy's non-network 10% co-pay is applied."""
    payload = {
        "policy_id": synthetic_tkr_policy,
        "scenario": {
            "treatment_name": "Total Knee Replacement",
            "quoted_cost": 250000.0,
            "patient_age": 54,
            "city": "Mumbai",
            "room_category": "Single Private Room",
            "length_of_stay": 4,
            "is_network_hospital": False,
            "pre_existing_condition": False,
        },
    }
    res = client.post("/api/treatment-estimates", json=payload)
    assert res.status_code == 200
    data = res.json()

    # 10% non-network co-pay on ₹250,000 -> ₹25,000
    assert data["copay_applied"] == 25000.0
    assert data["applicable_copay_percentage"] == 10.0
    assert data["estimated_insurer_contribution"] == 225000.0
    assert data["estimated_patient_responsibility"] == 25000.0
    assert round(data["estimated_insurer_contribution"] + data["estimated_patient_responsibility"], 2) == 250000.0

    trace = data.get("calculation_trace", [])
    assert any("Cashless Network Hospital = False -> Out-of-network co-pay of 10.0% applied" in step for step in trace)
    assert any("Co-pay calculation: 10.0% of ₹250,000.00 = ₹25,000.00" in step for step in trace)


# TEST 3: No deductible - verify deductible is Not Determined and ₹5,000 is never manufactured
def test_regression_test_3_no_deductible(client: TestClient, synthetic_tkr_policy: int) -> None:
    """Verify missing deductible in policy is treated as Not Determined, not fabricated as ₹5,000."""
    payload = {
        "policy_id": synthetic_tkr_policy,
        "scenario": {
            "treatment_name": "Total Knee Replacement",
            "quoted_cost": 250000.0,
            "is_network_hospital": True,
        },
    }
    res = client.post("/api/treatment-estimates", json=payload)
    assert res.status_code == 200
    data = res.json()

    assert data["deductible_status"] == "not_determined"
    assert data["deductible_amount"] is None
    assert data["deductible_applied"] == 0.0

    # Ensure ₹5,000 is never introduced anywhere in driving factors or calculation trace
    trace_text = " ".join(data.get("calculation_trace", []))
    assert "5000" not in trace_text
    assert "5,000" not in trace_text


# TEST 4: Degenerative TKR - verify 36-month waiting period
def test_regression_test_4_degenerative_tkr(client: TestClient, synthetic_tkr_policy: int) -> None:
    """Verify TKR waiting period is 36 months if degenerative condition."""
    payload = {
        "policy_id": synthetic_tkr_policy,
        "scenario": {
            "treatment_name": "Total Knee Replacement",
            "quoted_cost": 250000.0,
            "pre_existing_condition": True,
        },
    }
    res = client.post("/api/treatment-estimates", json=payload)
    assert res.status_code == 200
    data = res.json()

    factors = data.get("driving_factors", [])
    waiting_factor = next((f for f in factors if "Waiting" in f["factor_name"]), None)
    assert waiting_factor is not None
    assert "36 months" in waiting_factor["description"]
    assert "degenerative" in waiting_factor["description"].lower()


# TEST 5: Accident TKR - verify accident rule applies
def test_regression_test_5_accident_tkr(client: TestClient, synthetic_tkr_policy: int) -> None:
    """Verify TKR rules acknowledge that accident-related cases follow the accident waiver rule."""
    payload = {
        "policy_id": synthetic_tkr_policy,
        "scenario": {
            "treatment_name": "Total Knee Replacement",
            "quoted_cost": 250000.0,
            "pre_existing_condition": False,
        },
    }
    res = client.post("/api/treatment-estimates", json=payload)
    assert res.status_code == 200
    data = res.json()

    factors = data.get("driving_factors", [])
    waiting_factor = next((f for f in factors if "Waiting" in f["factor_name"]), None)
    assert waiting_factor is not None
    assert "accident rule" in waiting_factor["description"].lower() or "accident" in waiting_factor["description"].lower()


# TEST 6: Coverage cap - 60% of sum insured, maximum ₹600,000
def test_regression_test_6_coverage_cap(client: TestClient, synthetic_tkr_policy: int) -> None:
    """Verify TKR coverage cap of ₹600,000 limits reimbursement for quotes exceeding cap."""
    # Quote ₹700,000 exceeds ₹600,000 cap
    payload = {
        "policy_id": synthetic_tkr_policy,
        "scenario": {
            "treatment_name": "Total Knee Replacement",
            "quoted_cost": 700000.0,
            "is_network_hospital": True,
        },
    }
    res = client.post("/api/treatment-estimates", json=payload)
    assert res.status_code == 200
    data = res.json()

    assert data["estimated_total_cost"] == 700000.0
    assert data["potentially_eligible_amount"] == 600000.0
    assert data["excess_over_limit"] == 100000.0
    assert data["estimated_insurer_contribution"] == 600000.0
    assert data["estimated_patient_responsibility"] == 100000.0


# TEST 7: Embedded financial example in PDF does not override user scenario quote
def test_regression_test_7_embedded_financial_example(client: TestClient, synthetic_tkr_policy: int) -> None:
    """
    Verify that PDF example values (₹240,000 typical, ₹211,500 insurer, ₹28,500 patient)
    do NOT override a user's scenario quote of ₹250,000.
    """
    payload = {
        "policy_id": synthetic_tkr_policy,
        "scenario": {
            "treatment_name": "Total Knee Replacement",
            "quoted_cost": 250000.0,
            "is_network_hospital": True,
        },
    }
    res = client.post("/api/treatment-estimates", json=payload)
    assert res.status_code == 200
    data = res.json()

    # Must calculate from ₹250,000, NOT return ₹240,000 / ₹211,500 / ₹28,500
    assert data["estimated_total_cost"] == 250000.0
    assert data["estimated_insurer_contribution"] != 211500.0
    assert data["estimated_patient_responsibility"] != 28500.0
    assert data["estimated_insurer_contribution"] == 250000.0
    assert data["estimated_patient_responsibility"] == 0.0


# TEST 8: What-If - baseline and modified calculations run independently using same policy
def test_regression_test_8_what_if_comparison(client: TestClient, synthetic_tkr_policy: int) -> None:
    """Verify What-If comparison executes two independent calculations with correct deltas."""
    payload = {
        "policy_id": synthetic_tkr_policy,
        "previous_scenario": {
            "treatment_name": "Total Knee Replacement",
            "quoted_cost": 250000.0,
            "room_category": "Single Private Room",
            "is_network_hospital": True,
        },
        "updated_scenario": {
            "treatment_name": "Total Knee Replacement",
            "quoted_cost": 300000.0,
            "room_category": "Deluxe Suite",
            "is_network_hospital": True,
        },
    }
    res = client.post("/api/treatment-estimates/what-if", json=payload)
    assert res.status_code == 200
    data = res.json()

    # Previous: ₹250,000 quote within ₹600k cap, 0% copay -> Insurer ₹250k, Patient ₹0
    prev_est = data["previous_estimate"]
    assert prev_est["estimated_total_cost"] == 250000.0
    assert prev_est["estimated_insurer_contribution"] == 250000.0
    assert prev_est["estimated_patient_responsibility"] == 0.0

    # Updated: ₹300,000 quote within ₹600k cap, 0% copay (no room rent penalty fabricated)
    upd_est = data["updated_estimate"]
    assert upd_est["estimated_total_cost"] == 300000.0
    assert upd_est["estimated_insurer_contribution"] == 300000.0
    assert upd_est["estimated_patient_responsibility"] == 0.0

    # Deltas
    assert data["total_cost_delta"] == 50000.0
    assert data["insurer_contribution_delta"] == 50000.0
    assert data["patient_responsibility_delta"] == 0.0


# TEST 9: Policy isolation - Policy B calculation does not inherit Policy A rules
def test_regression_test_9_policy_isolation(client: TestClient) -> None:
    """Verify uploading/creating Policy A and Policy B keeps their rules completely isolated."""
    db = SessionLocal()
    try:
        # Policy A: has ₹15,000 deductible and 20% co-pay
        pol_a = Policy(
            filename="policy_a.pdf",
            policy_number="POL-A-111",
            insurer_name="Insurer A",
            plan_name="Bronze Plan",
            status="analyzed",
        )
        db.add(pol_a)
        db.commit()
        db.refresh(pol_a)

        rule_a = CoverageRule(
            policy_id=pol_a.id,
            coverage_status="covered",
            deductible=15000.0,
            copay_percentage=20.0,
            coverage_limit=200000.0,
            source_reference="Section A",
        )
        db.add(rule_a)
        db.commit()

        # Policy B: clean policy without deductible, 0% network co-pay
        pol_b = Policy(
            filename="policy_b.pdf",
            policy_number="POL-B-222",
            insurer_name="Insurer B",
            plan_name="Gold Plan",
            status="analyzed",
            raw_metadata={
                "out_of_pocket_max": {"individual_in_network": 1000000.0},
                "network_copay": 0.0,
            },
        )
        db.add(pol_b)
        db.commit()
        db.refresh(pol_b)

        rule_b = CoverageRule(
            policy_id=pol_b.id,
            coverage_status="covered",
            deductible=None,
            copay_percentage=0.0,
            coverage_limit=600000.0,
            source_reference="Section B",
        )
        db.add(rule_b)
        db.commit()

        pol_a_id = pol_a.id
        pol_b_id = pol_b.id
    finally:
        db.close()

    # Calculate for Policy B
    payload = {
        "policy_id": pol_b_id,
        "scenario": {
            "treatment_name": "Total Knee Replacement",
            "quoted_cost": 250000.0,
            "is_network_hospital": True,
        },
    }
    res = client.post("/api/treatment-estimates", json=payload)
    assert res.status_code == 200
    data = res.json()

    # Policy B must NOT inherit Policy A's 15,000 deductible or 20% co-pay
    assert data["deductible_applied"] == 0.0
    assert data["copay_applied"] == 0.0
    assert data["estimated_insurer_contribution"] == 250000.0
    assert data["estimated_patient_responsibility"] == 0.0


# TEST 10: Policy ownership - User A cannot calculate using User B's policy_id
def test_regression_test_10_policy_ownership(client: TestClient) -> None:
    """Verify that User A receives 403 Forbidden attempting to estimate using User B's policy_id."""
    token_user_a = _create_user_and_token(client, "alice_patient@example.com", "Alice")
    token_user_b = _create_user_and_token(client, "bob_patient@example.com", "Bob")

    headers_user_a = {"Authorization": f"Bearer {token_user_a}"}
    headers_user_b = {"Authorization": f"Bearer {token_user_b}"}

    # User B creates a policy
    create_res = client.post(
        "/api/policies",
        headers=headers_user_b,
        json={
            "filename": "bobs_private_health_policy.pdf",
            "insurer_name": "Bob Secure Health",
            "policy_number": "BOB-POL-999",
        },
    )
    assert create_res.status_code == 201
    bobs_policy_id = create_res.json()["id"]

    # User A tries to calculate an estimate using Bob's policy_id -> must be 403 Forbidden
    hack_payload = {
        "policy_id": bobs_policy_id,
        "scenario": {
            "treatment_name": "Total Knee Replacement",
            "quoted_cost": 250000.0,
        },
    }
    res_forbidden = client.post(
        "/api/treatment-estimates",
        headers=headers_user_a,
        json=hack_payload,
    )
    assert res_forbidden.status_code == 403
    assert "permission" in res_forbidden.json()["detail"].lower()

    # User A tries to run What-If on Bob's policy_id -> must be 403 Forbidden
    what_if_hack = {
        "policy_id": bobs_policy_id,
        "previous_scenario": {"treatment_name": "Cataract Surgery", "quoted_cost": 45000.0},
        "updated_scenario": {"treatment_name": "Cataract Surgery", "quoted_cost": 55000.0},
    }
    res_whatif_forbidden = client.post(
        "/api/treatment-estimates/what-if",
        headers=headers_user_a,
        json=what_if_hack,
    )
    assert res_whatif_forbidden.status_code == 403
    assert "permission" in res_whatif_forbidden.json()["detail"].lower()


# TEST 11: Policy with no deductible -> deductible = Not Determined/None, never 5000 or 15000
def test_regression_policy_no_deductible_is_null_not_determined(client: TestClient) -> None:
    """Verify that a policy with no established deductible yields None/not_determined, never ₹5000 or ₹15000."""
    db = SessionLocal()
    try:
        policy = Policy(
            filename="no_deductible_policy.pdf",
            policy_number="ND-2026-001",
            insurer_name="Clean Health",
            plan_name="Zero Fallback Plan",
            raw_metadata={"network_copay": 0.0},
        )
        db.add(policy)
        db.commit()
        db.refresh(policy)
        pol_id = policy.id

        rule = CoverageRule(
            policy_id=pol_id,
            coverage_status="covered",
            deductible=None,
            copay_percentage=0.0,
            coverage_limit=500000.0,
            source_reference="Section 1.1",
        )
        db.add(rule)
        db.commit()
    finally:
        db.close()

    # Estimate treatment
    res = client.post(
        "/api/treatment-estimates",
        json={
            "policy_id": pol_id,
            "scenario": {"treatment_name": "General Surgery", "quoted_cost": 50000.0},
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["deductible_status"] == "not_determined"
    assert data["deductible_amount"] is None
    assert data["deductible_applied"] == 0.0
    # Must never be ₹5,000 or ₹15,000
    assert data["deductible_applied"] != 5000.0
    assert data["deductible_applied"] != 15000.0


# TEST 12: Policy with no explicit coverage limit -> coverage limit = None, never 250000 or 500000
def test_regression_policy_no_explicit_coverage_limit_is_null(client: TestClient) -> None:
    """Verify that when no explicit limit is in the policy, coverage_limit is None/null, never ₹250000 or ₹500000."""
    db = SessionLocal()
    try:
        policy = Policy(
            filename="unlimited_policy.pdf",
            policy_number="UNLIM-2026-001",
            insurer_name="Comprehensive Health",
            plan_name="No Sub-limit Plan",
            raw_metadata={"network_copay": 0.0},
        )
        db.add(policy)
        db.commit()
        db.refresh(policy)
        pol_id = policy.id

        rule = CoverageRule(
            policy_id=pol_id,
            coverage_status="covered",
            deductible=None,
            copay_percentage=0.0,
            coverage_limit=None,  # No explicit limit
            source_reference="Section 2.1",
        )
        db.add(rule)
        db.commit()
    finally:
        db.close()

    res = client.post(
        "/api/treatment-estimates",
        json={
            "policy_id": pol_id,
            "scenario": {"treatment_name": "Appendectomy", "quoted_cost": 80000.0},
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["potentially_eligible_amount"] == 80000.0
    assert data["estimated_insurer_contribution"] == 80000.0
    # Coverage cap must be None / null, never 250000 or 500000
    assert data.get("policy_coverage_cap") is None
    assert data.get("policy_coverage_percentage") is None
    assert data["raw_calculation"].get("coverage_limit") is None


# TEST 13: What-If API failure does not return hardcoded financial numbers
def test_regression_what_if_api_failure_no_hardcoded_numbers(client: TestClient) -> None:
    """Verify that calling what-if with an invalid policy returns 404 error, never returning mock ₹225000 or ₹75000."""
    res = client.post(
        "/api/treatment-estimates/what-if",
        json={
            "policy_id": 99999999,
            "previous_scenario": {"treatment_name": "Cataract Surgery", "quoted_cost": 45000.0},
            "updated_scenario": {"treatment_name": "Cataract Surgery", "quoted_cost": 55000.0},
        },
    )
    assert res.status_code == 404
    body = res.json()
    assert "not found" in body["detail"].lower()
    # Ensure no mock numbers exist in error response
    assert "estimatedInsurerContribution" not in body
    assert "estimated_insurer_contribution" not in body


# TEST 14: Dashboard does not fabricate financial totals when source data is missing
def test_regression_dashboard_does_not_fabricate_financial_totals(client: TestClient) -> None:
    """Verify authenticated dashboard does not fabricate patient_share * 5 or 50000.0 when data is missing."""
    token = _create_user_and_token(client, "clean_dashboard_user@example.com", "Clean Dashboard")
    headers = {"Authorization": f"Bearer {token}"}

    # Create policy for user without any simulations
    pol_res = client.post(
        "/api/policies",
        headers=headers,
        json={"filename": "empty_policy.pdf", "insurer_name": "Empty Insurer"},
    )
    assert pol_res.status_code == 201

    # Fetch dashboard
    dash_res = client.get("/api/dashboard", headers=headers)
    assert dash_res.status_code == 200
    data = dash_res.json()

    assert data["is_authenticated"] is True
    assert data["cost_comparison_chart"] == []
    assert data["total_estimated_patient_costs"] == 0.0
    assert data["stats"]["total_estimated_savings"] == 0.0
    assert data["stats"]["total_claim_amount_simulated"] == 0.0


# TEST 15: Coverage Percentage remains contractual only (never insurer_share / quote)
def test_regression_coverage_percentage_remains_contractual_only(client: TestClient, synthetic_tkr_policy: int) -> None:
    """
    Verify coverage percentage reflects ONLY the contractual rule (60%),
    even when a low quote of ₹250,000 is 100% paid by insurer.
    It must NEVER return 100% as the policy coverage percentage.
    """
    res = client.post(
        "/api/analyses",
        json={"policy_id": synthetic_tkr_policy, "treatment_name": "Total Knee Replacement"},
    )
    assert res.status_code == 201
    data = res.json()
    # Contractual rule: 60% of sum insured
    assert data["coverage_percentage"] == 60.0
    assert data["policy_coverage_cap"] == 600000.0
    # Must NOT be 100.0%
    assert data["coverage_percentage"] != 100.0


# TEST 16: TKR synthetic policy invariant verification
def test_regression_tkr_synthetic_policy_contractual_invariants(client: TestClient, synthetic_tkr_policy: int) -> None:
    """
    Verify TKR synthetic policy produces:
    - Coverage Percentage: 60%
    - Policy coverage cap: ₹600,000
    - Degenerative waiting period: 36 months
    - Network co-pay: 0%
    - Non-network co-pay: 10%
    - Deductible: Not Determined
    """
    # 1. Check analysis results
    ana_res = client.post(
        "/api/analyses",
        json={"policy_id": synthetic_tkr_policy, "treatment_name": "Total Knee Replacement"},
    )
    assert ana_res.status_code == 201
    ana_data = ana_res.json()
    assert ana_data["coverage_percentage"] == 60.0
    assert ana_data["policy_coverage_cap"] == 600000.0
    assert "36 months" in str(ana_data["waiting_periods"])
    assert ana_data["copay_percentage"] == 0.0
    assert ana_data["deductible"] is None
    assert ana_data["deductible_status"] == "not_determined"

    # 2. Check network hospital calculation (0% copay, deductible not determined)
    net_est = client.post(
        "/api/treatment-estimates",
        json={
            "policy_id": synthetic_tkr_policy,
            "scenario": {
                "treatment_name": "Total Knee Replacement",
                "quoted_cost": 250000.0,
                "is_network_hospital": True,
            },
        },
    )
    assert net_est.status_code == 200
    net_data = net_est.json()
    assert net_data["copay_applied"] == 0.0
    assert net_data["deductible_status"] == "not_determined"
    assert net_data["deductible_applied"] == 0.0
    assert net_data["estimated_insurer_contribution"] == 250000.0
    assert net_data["estimated_patient_responsibility"] == 0.0

    # 3. Check non-network hospital calculation (10% non-network copay applies)
    non_net_est = client.post(
        "/api/treatment-estimates",
        json={
            "policy_id": synthetic_tkr_policy,
            "scenario": {
                "treatment_name": "Total Knee Replacement",
                "quoted_cost": 250000.0,
                "is_network_hospital": False,
            },
        },
    )
    assert non_net_est.status_code == 200
    non_net_data = non_net_est.json()
    assert non_net_data["copay_applied"] == 25000.0  # 10% of 250,000
    assert non_net_data["estimated_patient_responsibility"] == 25000.0
    assert non_net_data["estimated_insurer_contribution"] == 225000.0

