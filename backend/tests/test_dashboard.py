from fastapi.testclient import TestClient


def test_dashboard_empty_and_populated_state(client: TestClient) -> None:
    """Verify /api/dashboard endpoint aggregates statistics and returns operational summary."""
    # 1. Fetch initial dashboard state
    init_res = client.get("/api/dashboard")
    assert init_res.status_code == 200
    init_data = init_res.json()
    assert "stats" in init_data
    assert "system_status" in init_data
    assert init_data["system_status"] == "operational"

    # 2. Seed data: policy, analysis, simulation
    policy_res = client.post(
        "/api/policies",
        json={"filename": "dashboard_test_policy.pdf", "insurer_name": "Care Health"},
    )
    policy_id = policy_res.json()["id"]

    analysis_res = client.post(
        "/api/analyses",
        json={"policy_id": policy_id, "treatment_name": "Cataract Surgery"},
    )
    assert analysis_res.status_code == 201

    sim_res = client.post(
        "/api/simulations",
        json={"policy_id": policy_id, "hospital_quote": 100000.0, "treatment_name": "Cataract Surgery"},
    )
    assert sim_res.status_code == 201

    # 3. Fetch dashboard and verify updated metrics
    dash_res = client.get("/api/dashboard")
    assert dash_res.status_code == 200
    dash_data = dash_res.json()
    stats = dash_data["stats"]

    assert stats["total_policies"] >= 1
    assert stats["total_analyses"] >= 1
    assert stats["total_simulations"] >= 1
    assert stats["total_claim_amount_simulated"] >= 100000.0
    assert stats["average_insurance_coverage_pct"] >= 0.0

    assert len(dash_data["recent_policies"]) >= 1
    assert len(dash_data["recent_analyses"]) >= 1
    assert len(dash_data["recent_simulations"]) >= 1


def test_dashboard_direct_root_route(client: TestClient) -> None:
    """Verify /dashboard is accessible both directly and via /api/dashboard."""
    res = client.get("/dashboard")
    assert res.status_code == 200
    data = res.json()
    assert "stats" in data
    assert data["system_status"] == "operational"
