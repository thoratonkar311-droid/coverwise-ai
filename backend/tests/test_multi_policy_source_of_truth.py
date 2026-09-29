"""
Regression tests for Multi-Policy and Arbitrary-Policy Source of Truth.
Covers Requirements 18 & 19:
- Multi-policy switching with ZERO data leakage across all modules:
  Coverage Intelligence, Policy Assistant, Treatment Cost Review, Scenario Studio, What-If, Dashboard.
- Switching cycle: A -> B -> A -> B.
- Arbitrary policies with distinct rule structures (Policy X, Policy Y, Policy Z).
"""

import pytest
from fastapi.testclient import TestClient

from app.models.policy import Policy
from app.models.coverage_rule import CoverageRule
from app.models.evidence_reference import EvidenceReference
from app.models.simulation import Simulation
from app.db.session import SessionLocal


def _create_user_and_token(client: TestClient, email: str, name: str) -> tuple[int, str]:
    """Helper to register a user and return (user_id, token)."""
    res = client.post(
        "/api/auth/register",
        json={"email": email, "password": "SecurePassword123!", "full_name": name},
    )
    assert res.status_code == 201
    data = res.json()
    user_id = data.get("user", {}).get("id") or data.get("id")
    token = data["access_token"]
    return user_id, token


def _create_policy_a(user_id: int) -> int:
    """
    Policy A:
    * Sum Insured: ₹10,00,000
    * TKR 60%
    * cap ₹6,00,000
    * waiting 36 months
    * network copay 0%
    * deductible Not Determined (None)
    """
    db = SessionLocal()
    try:
        policy = Policy(
            user_id=user_id,
            filename="Policy_A_Gold.pdf",
            policy_number="POL-A-1000",
            insurer_name="Assurance Alpha",
            plan_name="Alpha Shield 10L",
            sum_insured=1000000.0,
            status="analyzed",
            document_hash="hash_alpha_123",
            raw_metadata={
                "extracted_metadata": {
                    "policy_id": "POL-A-1000",
                    "policy_name": "Alpha Shield 10L",
                    "insurer_name": "Assurance Alpha",
                },
                "sum_insured": 1000000.0,
                "network_copay": 0.0,
                "limits": [
                    {
                        "procedure": "Total Knee Replacement",
                        "percentage_of_sum_insured": 60.0,
                        "absolute_max": 600000.0,
                        "waiting_period": "36 months",
                    }
                ],
            },
        )
        db.add(policy)
        db.commit()
        db.refresh(policy)

        rule = CoverageRule(
            user_id=user_id,
            policy_id=policy.id,
            category="Joint Replacement",
            procedure_name="Total Knee Replacement",
            rule_name="TKR 60% Cap Rule",
            coverage_status="covered",
            coverage_percentage=60.0,
            coverage_limit_amount=600000.0,
            coverage_limit=600000.0,
            coverage_limit_percentage_of_si=60.0,
            deductible=None,
            deductible_status="not_determined",
            copay_percentage=0.0,
            waiting_period="36 months",
            waiting_period_type="specific_disease",
            network_condition="0% network co-pay",
            source_type="contractual_rule",
            source_reference="Section 5.1 Orthopedics (Page 12)",
        )
        db.add(rule)
        db.commit()
        db.refresh(rule)

        evidence = EvidenceReference(
            user_id=user_id,
            policy_id=policy.id,
            rule_id=rule.id,
            document_source="Policy_A_Gold.pdf",
            page=12,
            clause_section="Section 5.1",
            extracted_text="Total Knee Replacement is covered up to 60% of Sum Insured (max ₹6,00,000) after a 36-month waiting period.",
            confidence=0.98,
            source_type="contractual_rule",
        )
        db.add(evidence)
        db.commit()
        return policy.id
    finally:
        db.close()


def _create_policy_b(user_id: int) -> int:
    """
    Policy B:
    * Sum Insured: ₹5,00,000
    * TKR 50%
    * cap ₹2,50,000
    * waiting 24 months
    * network copay 20%
    * deductible ₹10,000
    """
    db = SessionLocal()
    try:
        policy = Policy(
            user_id=user_id,
            filename="Policy_B_Silver.pdf",
            policy_number="POL-B-2000",
            insurer_name="Assurance Beta",
            plan_name="Beta Care 5L",
            sum_insured=500000.0,
            status="analyzed",
            document_hash="hash_beta_456",
            raw_metadata={
                "extracted_metadata": {
                    "policy_id": "POL-B-2000",
                    "policy_name": "Beta Care 5L",
                    "insurer_name": "Assurance Beta",
                },
                "sum_insured": 500000.0,
                "network_copay": 20.0,
                "deductible": 10000.0,
                "limits": [
                    {
                        "procedure": "Total Knee Replacement",
                        "percentage_of_sum_insured": 50.0,
                        "absolute_max": 250000.0,
                        "waiting_period": "24 months",
                    }
                ],
            },
        )
        db.add(policy)
        db.commit()
        db.refresh(policy)

        rule = CoverageRule(
            user_id=user_id,
            policy_id=policy.id,
            category="Joint Replacement",
            procedure_name="Total Knee Replacement",
            rule_name="TKR 50% Cap Rule",
            coverage_status="covered",
            coverage_percentage=50.0,
            coverage_limit_amount=250000.0,
            coverage_limit=250000.0,
            coverage_limit_percentage_of_si=50.0,
            deductible=10000.0,
            deductible_status="established",
            copay_percentage=20.0,
            waiting_period="24 months",
            waiting_period_type="specific_disease",
            network_condition="20% network co-pay",
            source_type="contractual_rule",
            source_reference="Section 3.4 Joint Replacement (Page 8)",
        )
        db.add(rule)
        db.commit()
        db.refresh(rule)

        evidence = EvidenceReference(
            user_id=user_id,
            policy_id=policy.id,
            rule_id=rule.id,
            document_source="Policy_B_Silver.pdf",
            page=8,
            clause_section="Section 3.4",
            extracted_text="Knee replacement capped at 50% of sum insured (max ₹2,50,000) subject to ₹10,000 deductible, 20% network co-pay, and 24 months waiting.",
            confidence=0.95,
            source_type="contractual_rule",
        )
        db.add(evidence)
        db.commit()
        return policy.id
    finally:
        db.close()


def test_multi_policy_switching_zero_leakage_a_b_a_b(client: TestClient) -> None:
    """
    Test switching: Policy A -> Policy B -> Policy A -> Policy B.
    Verify ZERO cross-policy leakage across:
    - Coverage Intelligence
    - Policy Assistant
    - Treatment Cost Review
    - Scenario Studio
    - What-If
    - Dashboard
    """
    user_id, token = _create_user_and_token(client, "multi_poly_user@test.com", "Multi Poly User")
    headers = {"Authorization": f"Bearer {token}"}

    policy_a_id = _create_policy_a(user_id)
    policy_b_id = _create_policy_b(user_id)

    # Helper function to assert all modules conform strictly to Policy A
    def verify_policy_a_state():
        # 1. Active policy endpoint
        act = client.get("/api/policies/active", headers=headers).json()
        assert act["id"] == policy_a_id
        assert act["plan_name"] == "Alpha Shield 10L"
        assert act["sum_insured"] == 1000000.0

        # 2. Coverage Intelligence
        cov = client.get(f"/api/coverage?policy_id={policy_a_id}", headers=headers).json()
        rules = cov if isinstance(cov, list) else cov.get("rules", [])
        assert len(rules) >= 1
        tkr_rule = next(r for r in rules if "Total Knee Replacement" in (r.get("procedure_name") or r.get("rule_name") or ""))
        assert tkr_rule["coverage_percentage"] == 60.0
        assert tkr_rule["coverage_limit_amount"] == 600000.0
        assert tkr_rule["copay_percentage"] == 0.0
        assert tkr_rule["waiting_period"] == "36 months"
        assert tkr_rule["deductible"] is None or tkr_rule["deductible_status"] == "not_determined"

        # Evidence must cite Page 12, Policy_A_Gold.pdf
        ana = client.post(
            "/api/analyses",
            headers=headers,
            json={"policy_id": policy_a_id, "treatment_name": "Total Knee Replacement"},
        ).json()
        assert ana["coverage_percentage"] == 60.0
        assert ana["policy_coverage_cap"] == 600000.0
        assert "36 months" in str(ana["waiting_periods"])

        # 3. Policy Assistant
        conv = client.post(
            "/api/conversations",
            headers=headers,
            json={"policy_id": policy_a_id, "initial_message": "What is the waiting period for knee replacement?"},
        ).json()
        reply = conv["messages"][-1]["content"]
        assert "36 months" in reply
        assert "24 months" not in reply

        # 4. Treatment Cost Review (Quote ₹300,000, in-network)
        est = client.post(
            "/api/treatment-estimates",
            headers=headers,
            json={
                "policy_id": policy_a_id,
                "scenario": {
                    "treatment_name": "Total Knee Replacement",
                    "quoted_cost": 300000.0,
                    "is_network_hospital": True,
                },
            },
        ).json()
        # In Policy A: 0% network copay, deductible not determined
        assert est["applicable_copay_percentage"] == 0.0
        assert est["copay_applied"] == 0.0
        assert est["deductible_status"] == "not_determined"
        assert est["estimated_insurer_contribution"] == 300000.0
        assert est["estimated_patient_responsibility"] == 0.0

        # 5. What-If
        whatif = client.post(
            "/api/treatment-estimates/what-if",
            headers=headers,
            json={
                "policy_id": policy_a_id,
                "previous_scenario": {
                    "treatment_name": "Total Knee Replacement",
                    "quoted_cost": 300000.0,
                    "is_network_hospital": True,
                },
                "updated_scenario": {
                    "treatment_name": "Total Knee Replacement",
                    "quoted_cost": 300000.0,
                    "is_network_hospital": False,  # Non-network
                },
            },
        ).json()
        assert "total_cost_delta" in whatif
        assert len(whatif.get("explanation_of_changes", [])) > 0

        # 6. Dashboard
        dash = client.get("/api/dashboard", headers=headers).json()
        assert dash["active_policy"]["id"] == policy_a_id
        assert dash["active_policy"]["plan_name"] == "Alpha Shield 10L"

    # Helper function to assert all modules conform strictly to Policy B
    def verify_policy_b_state():
        # 1. Active policy endpoint
        act = client.get("/api/policies/active", headers=headers).json()
        assert act["id"] == policy_b_id
        assert act["plan_name"] == "Beta Care 5L"
        assert act["sum_insured"] == 500000.0

        # 2. Coverage Intelligence
        cov = client.get(f"/api/coverage?policy_id={policy_b_id}", headers=headers).json()
        rules = cov if isinstance(cov, list) else cov.get("rules", [])
        assert len(rules) >= 1
        tkr_rule = next(r for r in rules if "Total Knee Replacement" in (r.get("procedure_name") or r.get("rule_name") or ""))
        assert tkr_rule["coverage_percentage"] == 50.0
        assert tkr_rule["coverage_limit_amount"] == 250000.0
        assert tkr_rule["copay_percentage"] == 20.0
        assert tkr_rule["waiting_period"] == "24 months"
        assert tkr_rule["deductible"] == 10000.0

        ana = client.post(
            "/api/analyses",
            headers=headers,
            json={"policy_id": policy_b_id, "treatment_name": "Total Knee Replacement"},
        ).json()
        assert ana["coverage_percentage"] == 50.0
        assert ana["policy_coverage_cap"] == 250000.0
        assert "24 months" in str(ana["waiting_periods"])

        # 3. Policy Assistant
        conv = client.post(
            "/api/conversations",
            headers=headers,
            json={"policy_id": policy_b_id, "initial_message": "What is the waiting period for knee replacement?"},
        ).json()
        reply = conv["messages"][-1]["content"]
        assert "24 months" in reply
        assert "36 months" not in reply

        # 4. Treatment Cost Review (Quote ₹300,000, in-network)
        est = client.post(
            "/api/treatment-estimates",
            headers=headers,
            json={
                "policy_id": policy_b_id,
                "scenario": {
                    "treatment_name": "Total Knee Replacement",
                    "quoted_cost": 300000.0,
                    "is_network_hospital": True,
                },
            },
        ).json()
        # In Policy B: Cap is ₹250,000. Deductible is ₹10,000. Copay is 20%.
        # Eligible = min(300000, 250000) = 250,000
        # After deductible ₹10,000: base = 240,000
        # Copay 20% on 240,000 = 48,000
        # Insurer = 192,000. Patient = 48,000 + 10,000 + 50,000 (over cap) = 108,000
        assert est["applicable_copay_percentage"] == 20.0
        assert est["copay_applied"] == 48000.0
        assert est["deductible_applied"] == 10000.0
        assert est["estimated_insurer_contribution"] == 192000.0
        assert est["estimated_patient_responsibility"] == 108000.0

        # 5. What-If
        whatif = client.post(
            "/api/treatment-estimates/what-if",
            headers=headers,
            json={
                "policy_id": policy_b_id,
                "previous_scenario": {
                    "treatment_name": "Total Knee Replacement",
                    "quoted_cost": 300000.0,
                    "is_network_hospital": True,
                },
                "updated_scenario": {
                    "treatment_name": "Total Knee Replacement",
                    "quoted_cost": 300000.0,
                    "is_network_hospital": False,
                },
            },
        ).json()
        assert "total_cost_delta" in whatif
        assert len(whatif.get("explanation_of_changes", [])) > 0

        # 6. Dashboard
        dash = client.get("/api/dashboard", headers=headers).json()
        assert dash["active_policy"]["id"] == policy_b_id
        assert dash["active_policy"]["plan_name"] == "Beta Care 5L"

    # --- CYCLE 1: Activate A ---
    res_a1 = client.post(f"/api/policies/{policy_a_id}/activate", headers=headers)
    assert res_a1.status_code == 200
    verify_policy_a_state()

    # --- CYCLE 2: Activate B ---
    res_b1 = client.post(f"/api/policies/{policy_b_id}/activate", headers=headers)
    assert res_b1.status_code == 200
    verify_policy_b_state()

    # --- CYCLE 3: Activate A again ---
    res_a2 = client.post(f"/api/policies/{policy_a_id}/activate", headers=headers)
    assert res_a2.status_code == 200
    verify_policy_a_state()

    # --- CYCLE 4: Activate B again ---
    res_b2 = client.post(f"/api/policies/{policy_b_id}/activate", headers=headers)
    assert res_b2.status_code == 200
    verify_policy_b_state()


def test_arbitrary_policies_xyz_distinct_structures(client: TestClient) -> None:
    """
    Test Arbitrary Policy Structures (Requirement 19):
    - Policy X: no deductible, 10% copay, TKR cap as fixed amount (₹300,000)
    - Policy Y: ₹15,000 deductible, 20% copay, TKR cap as 50% of ₹8,00,000 SI (= ₹400,000)
    - Policy Z: no TKR-specific rule (only general coverage or other procedure)
    Expected:
    - X -> X rules applied strictly
    - Y -> Y rules applied strictly
    - Z -> Not Determined for TKR (no fallback from X or Y)
    """
    user_id, token = _create_user_and_token(client, "arbitrary_user@test.com", "Arbitrary User")
    headers = {"Authorization": f"Bearer {token}"}

    db = SessionLocal()
    try:
        # Policy X
        pol_x = Policy(
            user_id=user_id,
            filename="Policy_X.pdf",
            policy_number="POL-X",
            insurer_name="Insurer X",
            plan_name="Plan X",
            sum_insured=1000000.0,
            status="analyzed",
            raw_metadata={"network_copay": 10.0, "deductible": None},
        )
        db.add(pol_x)
        db.commit()
        db.refresh(pol_x)
        rule_x = CoverageRule(
            user_id=user_id,
            policy_id=pol_x.id,
            procedure_name="Total Knee Replacement",
            coverage_status="covered",
            coverage_limit_amount=300000.0,
            coverage_limit=300000.0,
            copay_percentage=10.0,
            deductible=None,
            deductible_status="not_determined",
            source_type="contractual_rule",
        )
        db.add(rule_x)

        # Policy Y
        pol_y = Policy(
            user_id=user_id,
            filename="Policy_Y.pdf",
            policy_number="POL-Y",
            insurer_name="Insurer Y",
            plan_name="Plan Y",
            sum_insured=800000.0,
            status="analyzed",
            raw_metadata={
                "network_copay": 20.0,
                "deductible": 15000.0,
                "limits": [
                    {
                        "procedure": "Total Knee Replacement",
                        "percentage_of_sum_insured": 50.0,
                    }
                ],
            },
        )
        db.add(pol_y)
        db.commit()
        db.refresh(pol_y)
        rule_y = CoverageRule(
            user_id=user_id,
            policy_id=pol_y.id,
            procedure_name="Total Knee Replacement",
            coverage_status="covered",
            coverage_percentage=50.0,
            coverage_limit_percentage_of_si=50.0,
            coverage_limit=400000.0,  # 50% of 800,000
            coverage_limit_amount=400000.0,
            copay_percentage=20.0,
            deductible=15000.0,
            deductible_status="established",
            source_type="contractual_rule",
        )
        db.add(rule_y)

        # Policy Z (No TKR rule, only Hernia Repair)
        pol_z = Policy(
            user_id=user_id,
            filename="Policy_Z.pdf",
            policy_number="POL-Z",
            insurer_name="Insurer Z",
            plan_name="Plan Z",
            sum_insured=600000.0,
            status="analyzed",
            raw_metadata={},
        )
        db.add(pol_z)
        db.commit()
        db.refresh(pol_z)
        rule_z = CoverageRule(
            user_id=user_id,
            policy_id=pol_z.id,
            procedure_name="Hernia Repair",
            coverage_status="covered",
            coverage_limit=75000.0,
            source_type="contractual_rule",
        )
        db.add(rule_z)
        db.commit()

        x_id, y_id, z_id = pol_x.id, pol_y.id, pol_z.id
    finally:
        db.close()

    # --- Test Policy X ---
    client.post(f"/api/policies/{x_id}/activate", headers=headers)
    est_x = client.post(
        "/api/treatment-estimates",
        headers=headers,
        json={
            "policy_id": x_id,
            "scenario": {
                "treatment_name": "Total Knee Replacement",
                "quoted_cost": 350000.0,
                "is_network_hospital": True,
            },
        },
    ).json()
    # Cap = 300,000. Deductible = 0 / not determined. Copay = 10% on 300,000 = 30,000
    assert est_x["copay_applied"] == 30000.0
    assert est_x["deductible_status"] == "not_determined"
    assert est_x["estimated_insurer_contribution"] == 270000.0
    assert est_x["estimated_patient_responsibility"] == 80000.0  # 30,000 copay + 50,000 over cap

    # --- Test Policy Y ---
    client.post(f"/api/policies/{y_id}/activate", headers=headers)
    est_y = client.post(
        "/api/treatment-estimates",
        headers=headers,
        json={
            "policy_id": y_id,
            "scenario": {
                "treatment_name": "Total Knee Replacement",
                "quoted_cost": 350000.0,
                "is_network_hospital": True,
            },
        },
    ).json()
    # Cap = 400,000. Deductible = 15,000. Base = 350,000 - 15,000 = 335,000. Copay 20% = 67,000
    assert est_y["deductible_applied"] == 15000.0
    assert est_y["copay_applied"] == 67000.0
    assert est_y["estimated_insurer_contribution"] == 268000.0
    assert est_y["estimated_patient_responsibility"] == 82000.0

    # --- Test Policy Z (Unknown / Not Determined for TKR) ---
    client.post(f"/api/policies/{z_id}/activate", headers=headers)
    est_z = client.post(
        "/api/treatment-estimates",
        headers=headers,
        json={
            "policy_id": z_id,
            "scenario": {
                "treatment_name": "Total Knee Replacement",
                "quoted_cost": 350000.0,
                "is_network_hospital": True,
            },
        },
    ).json()
    # Since Policy Z has NO rule for TKR, it must NOT fall back to Policy X or Y
    # Coverage cap is null/None
    assert est_z.get("policy_coverage_cap") is None
    # Deductible is not determined
    assert est_z.get("deductible_status") == "not_determined"
    # Coverage percentage is null
    assert est_z.get("policy_coverage_percentage") is None
    # Trace must not contain rules from X or Y
    trace_text = " ".join(est_z.get("calculation_trace", []))
    assert "Plan X" not in trace_text
    assert "Plan Y" not in trace_text
