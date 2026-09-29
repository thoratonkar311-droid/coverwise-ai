from fastapi.testclient import TestClient


def test_standalone_simulation_calculation(client: TestClient) -> None:
    """Verify deterministic cost simulation without pre-saved policy using explicit overrides."""
    payload = {
        "treatment_name": "Angioplasty",
        "hospital_quote": 200000.0,
        "room_category": "Twin Sharing",
        "deductible": 10000.0,
        "copay_percentage": 10.0,
        "coverage_limit": 150000.0,
    }
    response = client.post("/api/simulations", json=payload)
    assert response.status_code == 201
    data = response.json()

    # Quote = 200,000
    # Capped at limit = 150,000 (Excess 50,000 to patient)
    # Deductible = 10,000 (Remaining = 140,000)
    # Copay 10% on 140,000 = 14,000
    # Insurer share = 140,000 - 14,000 = 126,000
    # Patient share = 200,000 - 126,000 = 74,000
    assert data["estimated_insurance_share"] == 126000.0
    assert data["estimated_patient_share"] == 74000.0
    assert round(data["estimated_insurance_share"] + data["estimated_patient_share"], 2) == 200000.0
    assert data["deductible"] == 10000.0
    assert data["copay"] == 14000.0


def test_simulation_route_alias_and_non_payable_items(client: TestClient) -> None:
    """Verify /api/simulator frontend alias route and non_payable_items deduction."""
    payload = {
        "treatment": "Gallbladder Removal",
        "hospital_quote": 100000.0,
        "non_payable_items": 10000.0,  # 10,000 non-payable PPE/admin charges
        "deductible": 0.0,
        "copay_percentage": 0.0,
        "coverage_limit": 200000.0,
    }
    response = client.post("/api/simulator", json=payload)
    assert response.status_code == 201
    data = response.json()

    # Quote = 100,000; Ineligible = 10,000; Eligible = 90,000
    # Insurer = 90,000; Patient = 10,000
    assert data["estimated_insurance_share"] == 90000.0
    assert data["estimated_patient_share"] == 10000.0
    assert data["excluded_amount"] == 10000.0
    assert round(data["estimated_insurance_share"] + data["estimated_patient_share"], 2) == 100000.0


def test_simulation_with_policy_integration(client: TestClient) -> None:
    """Verify simulation inherits coverage rules from analyzed policy."""
    # 1. Register policy with contractual rules
    policy_res = client.post(
        "/api/policies",
        json={
            "filename": "bajaj_allianz_silver.pdf",
            "insurer_name": "Bajaj Allianz",
            "raw_metadata": {
                "limits": [
                    {
                        "service_or_category": "Total Knee Replacement",
                        "limit_value": 600000.0,
                        "copay_percentage": 0.0,
                        "coverage_status": "covered",
                    }
                ]
            },
        },
    )
    policy_id = policy_res.json()["id"]

    # 2. Run analysis for Knee replacement (contractual: 600,000 limit, 0% network copay, deductible not determined)
    client.post(
        "/api/analyses",
        json={"policy_id": policy_id, "treatment_name": "Total Knee Replacement"},
    )

    # 3. Simulate quote within contractual limit (300,000 <= 600,000 cap)
    sim_res = client.post(
        "/api/simulations",
        json={
            "policy_id": policy_id,
            "treatment_name": "Total Knee Replacement",
            "hospital_quote": 300000.0,
        },
    )
    assert sim_res.status_code == 201
    sim_data = sim_res.json()
    assert sim_data["policy_id"] == policy_id
    assert sim_data["estimated_insurance_share"] == 300000.0
    assert sim_data["estimated_patient_share"] == 0.0
    assert round(sim_data["estimated_insurance_share"] + sim_data["estimated_patient_share"], 2) == 300000.0

    # 4. Simulate quote exceeding contractual cap (700,000 > 600,000 cap)
    sim_cap_res = client.post(
        "/api/simulations",
        json={
            "policy_id": policy_id,
            "treatment_name": "Total Knee Replacement",
            "hospital_quote": 700000.0,
        },
    )
    assert sim_cap_res.status_code == 201
    cap_data = sim_cap_res.json()
    assert cap_data["estimated_insurance_share"] == 600000.0
    assert cap_data["estimated_patient_share"] == 100000.0


def test_simulation_get_by_id_and_policy_list(client: TestClient) -> None:
    """Verify simulation retrieval by ID and policy list."""
    policy_res = client.post(
        "/api/policies",
        json={"filename": "care_supreme.pdf", "insurer_name": "Care Supreme"},
    )
    policy_id = policy_res.json()["id"]

    sim_res = client.post(
        "/api/simulations",
        json={
            "policy_id": policy_id,
            "hospital_quote": 85000.0,
            "treatment_name": "Hernia Repair",
        },
    )
    sim_id = sim_res.json()["id"]

    # Get by ID
    get_res = client.get(f"/api/simulations/{sim_id}")
    assert get_res.status_code == 200
    assert get_res.json()["id"] == sim_id

    # List by policy
    list_res = client.get(f"/api/policies/{policy_id}/simulations")
    assert list_res.status_code == 200
    assert len(list_res.json()) >= 1


def test_simulation_invalid_inputs_validation(client: TestClient) -> None:
    """Verify non-positive quotes, negative deductibles, and >100 copay trigger 422."""
    # Zero quote
    res_zero = client.post(
        "/api/simulations",
        json={"hospital_quote": 0.0, "treatment_name": "Checkup"},
    )
    assert res_zero.status_code == 422

    # Negative quote
    res_neg = client.post(
        "/api/simulations",
        json={"hospital_quote": -500.0, "treatment_name": "Checkup"},
    )
    assert res_neg.status_code == 422

    # Copay percentage > 100
    res_copay = client.post(
        "/api/simulations",
        json={"hospital_quote": 50000.0, "treatment_name": "Checkup", "copay_percentage": 105.0},
    )
    assert res_copay.status_code == 422

    # Negative deductible
    res_ded = client.post(
        "/api/simulations",
        json={"hospital_quote": 50000.0, "treatment_name": "Checkup", "deductible": -100.0},
    )
    assert res_ded.status_code == 422


def test_simulation_path_validation_gt_zero(client: TestClient) -> None:
    """Verify path validation rejects simulation_id <= 0 with 422."""
    res = client.get("/api/simulations/0")
    assert res.status_code == 422


def test_get_nonexistent_simulation_404(client: TestClient) -> None:
    """Verify 404 response when querying simulation ID that does not exist."""
    res = client.get("/api/simulations/999999")
    assert res.status_code == 404
    data = res.json()
    assert "error" in data
    assert "not found" in data["error"]["message"].lower()


def test_simulation_nonexistent_policy_404(client: TestClient) -> None:
    """Verify 404 when running simulation for a policy ID that does not exist."""
    res = client.post(
        "/api/simulations",
        json={"policy_id": 999999, "hospital_quote": 50000.0, "treatment_name": "Checkup"},
    )
    assert res.status_code == 404
    data = res.json()
    assert "error" in data
    assert "not found" in data["error"]["message"].lower()
