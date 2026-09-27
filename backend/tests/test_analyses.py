from fastapi.testclient import TestClient


def test_analyze_coverage_scenarios(client: TestClient) -> None:
    """Verify coverage analysis for various medical procedure scenarios."""
    # 1. Register a test policy
    policy_res = client.post(
        "/api/policies",
        json={
            "filename": "star_comprehensive_plan.pdf",
            "insurer_name": "Star Health",
            "plan_name": "Star Comprehensive",
        },
    )
    policy_id = policy_res.json()["id"]

    # Scenario A: Cataract (sub-limit capped)
    cataract_res = client.post(
        "/api/analyses",
        json={"policy_id": policy_id, "treatment_name": "Cataract Surgery"},
    )
    assert cataract_res.status_code == 201
    cataract_data = cataract_res.json()
    assert cataract_data["coverage_status"] == "partially_covered"
    assert cataract_data["coverage_limit"] == 40000.0
    assert len(cataract_data["evidence_references"]) >= 1
    assert "Section 4.B" in cataract_data["evidence_references"][0]["clause_section"]

    # Scenario B: Knee replacement (co-pay and waiting period)
    knee_res = client.post(
        "/api/analyses",
        json={"policy_id": policy_id, "treatment_name": "Total Knee Replacement"},
    )
    assert knee_res.status_code == 201
    knee_data = knee_res.json()
    assert knee_data["coverage_status"] == "partially_covered"
    assert knee_data["copay_percentage"] == 10.0
    assert knee_data["waiting_periods"] is not None

    # Scenario C: Cosmetic surgery (not covered)
    cosmetic_res = client.post(
        "/api/analyses",
        json={"policy_id": policy_id, "treatment_name": "Cosmetic Rhinoplasty"},
    )
    assert cosmetic_res.status_code == 201
    cosmetic_data = cosmetic_res.json()
    assert cosmetic_data["coverage_status"] == "not_covered"
    assert len(cosmetic_data["exclusions"]) >= 1

    # Scenario D: Unlisted / ambiguous treatment -> not_determined
    unknown_res = client.post(
        "/api/analyses",
        json={"policy_id": policy_id, "treatment_name": "Experimental Nanobot Therapy"},
    )
    assert unknown_res.status_code == 201
    unknown_data = unknown_res.json()
    assert unknown_data["coverage_status"] == "not_determined"
    assert unknown_data["confidence"] <= 0.5
    assert len(unknown_data["explanation"]) > 0


def test_analyze_route_alias_and_treatment_field_alias(client: TestClient) -> None:
    """Verify frontend alias route /api/analyze and payload field 'treatment'."""
    policy_res = client.post(
        "/api/policies",
        json={"filename": "care_heart_policy.pdf", "insurer_name": "Care Health"},
    )
    policy_id = policy_res.json()["id"]

    # Call /api/analyze with 'treatment' instead of 'treatment_name'
    res = client.post(
        "/api/analyze",
        json={"policy_id": policy_id, "treatment": "Angioplasty and Cardiac Stent"},
    )
    assert res.status_code == 201
    data = res.json()
    assert data["coverage_status"] == "likely_covered"
    assert data["treatment_name"] == "Angioplasty and Cardiac Stent"


def test_analyze_idempotency_and_force_refresh(client: TestClient) -> None:
    """Verify identical requests return cached analysis unless force_refresh is specified."""
    policy_res = client.post(
        "/api/policies",
        json={"filename": "religare_idempotent.pdf", "insurer_name": "Care Health"},
    )
    policy_id = policy_res.json()["id"]

    # 1. First analysis call
    first_res = client.post(
        "/api/analyses",
        json={"policy_id": policy_id, "treatment_name": "Cataract Surgery"},
    )
    assert first_res.status_code == 201
    first_id = first_res.json()["id"]

    # 2. Second identical call -> should return cached result with same ID
    second_res = client.post(
        "/api/analyses",
        json={"policy_id": policy_id, "treatment_name": "Cataract Surgery"},
    )
    assert second_res.status_code == 201
    assert second_res.json()["id"] == first_id

    # 3. Third call with force_refresh=True -> creates a new analysis record
    third_res = client.post(
        "/api/analyses",
        json={"policy_id": policy_id, "treatment_name": "Cataract Surgery", "force_refresh": True},
    )
    assert third_res.status_code == 201
    assert third_res.json()["id"] > first_id


def test_get_analysis_and_list_by_policy(client: TestClient) -> None:
    """Verify retrieving analysis by ID and listing analyses for a policy."""
    policy_res = client.post(
        "/api/policies",
        json={"filename": "religare_care.pdf", "insurer_name": "Care Health"},
    )
    policy_id = policy_res.json()["id"]

    # Create analysis
    analysis_res = client.post(
        "/api/analyses",
        json={"policy_id": policy_id, "treatment_name": "Appendectomy"},
    )
    analysis_id = analysis_res.json()["id"]

    # Retrieve by ID
    get_res = client.get(f"/api/analyses/{analysis_id}")
    assert get_res.status_code == 200
    assert get_res.json()["id"] == analysis_id
    assert get_res.json()["treatment_name"] == "Appendectomy"

    # List by policy
    list_res = client.get(f"/api/policies/{policy_id}/analyses")
    assert list_res.status_code == 200
    assert len(list_res.json()) >= 1


def test_analyze_nonexistent_policy_404(client: TestClient) -> None:
    """Verify 404 response when policy ID does not exist."""
    res = client.post(
        "/api/analyses",
        json={"policy_id": 999999, "treatment_name": "Cardiac Stent"},
    )
    assert res.status_code == 404


def test_analysis_path_validation_gt_zero(client: TestClient) -> None:
    """Verify path validation gt=0 rejects 0 or negative ID with 422."""
    res = client.get("/api/analyses/0")
    assert res.status_code == 422


def test_get_nonexistent_analysis_404(client: TestClient) -> None:
    """Verify 404 response when querying analysis ID that does not exist."""
    res = client.get("/api/analyses/999999")
    assert res.status_code == 404
    data = res.json()
    assert "error" in data
    assert "not found" in data["error"]["message"].lower()
