from fastapi.testclient import TestClient


def test_coverage_rules_listing_and_filtering(client: TestClient) -> None:
    """Verify listing coverage rules and filtering by policy_id."""
    # 1. Create a policy
    policy_res = client.post(
        "/api/policies",
        json={"filename": "coverage_test_policy.pdf", "insurer_name": "Star Health"},
    )
    policy_id = policy_res.json()["id"]

    # 2. Run analysis which seeds a CoverageRule
    client.post(
        "/api/analyses",
        json={"policy_id": policy_id, "treatment_name": "Total Knee Replacement"},
    )

    # 3. Query /api/coverage
    res = client.get(f"/api/coverage?policy_id={policy_id}")
    assert res.status_code == 200
    rules = res.json()
    assert len(rules) >= 1
    assert rules[0]["policy_id"] == policy_id
    assert rules[0]["coverage_status"] == "partially_covered"
    assert rules[0]["copay_percentage"] == 10.0

    rule_id = rules[0]["id"]

    # 4. Get individual rule by ID
    single_res = client.get(f"/api/coverage/{rule_id}")
    assert single_res.status_code == 200
    assert single_res.json()["id"] == rule_id


def test_coverage_query_semantic_evidence(client: TestClient) -> None:
    """Verify semantic clause and evidence retrieval via /api/coverage/query."""
    policy_res = client.post(
        "/api/policies",
        json={"filename": "apollo_munich_optima.pdf", "insurer_name": "Apollo Munich"},
    )
    policy_id = policy_res.json()["id"]

    query_payload = {
        "policy_id": policy_id,
        "query": "Optical cataract surgery sublimit",
        "max_results": 3,
    }
    res = client.post("/api/coverage/query", json=query_payload)
    assert res.status_code == 200
    data = res.json()
    assert "evidence_items" in data
    assert len(data["evidence_items"]) >= 1
    assert "Section 4.B" in data["evidence_items"][0]["clause_section"]


def test_coverage_path_validation_and_not_found(client: TestClient) -> None:
    """Verify path validation gt=0 and 404 for nonexistent coverage rule."""
    res_zero = client.get("/api/coverage/0")
    assert res_zero.status_code == 422

    res_404 = client.get("/api/coverage/999999")
    assert res_404.status_code == 404
