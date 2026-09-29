import io
from fastapi.testclient import TestClient


def _create_user(client: TestClient, email: str, name: str) -> str:
    res = client.post(
        "/api/auth/register",
        json={"email": email, "password": "TestPassword123!", "full_name": name},
    )
    assert res.status_code == 201
    return res.json()["access_token"]


def test_dashboard_unauthenticated_state(client: TestClient) -> None:
    """Verify unauthenticated dashboard returns operational status with is_authenticated=False."""
    res = client.get("/api/dashboard")
    assert res.status_code == 200
    data = res.json()
    assert "stats" in data
    assert data.get("is_authenticated") is False


def test_dashboard_authenticated_empty_state(client: TestClient) -> None:
    """Verify an authenticated user with no data gets a clean empty dashboard scoped to them."""
    token = _create_user(client, "empty_dash_user@example.com", "Empty Dashboard User")
    headers = {"Authorization": f"Bearer {token}"}

    res = client.get("/api/dashboard", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["is_authenticated"] is True
    assert data["policies_analyzed_count"] == 0
    assert data["coverage_analyses_count"] == 0
    assert data["active_policy"] is None
    assert len(data["recent_policies"]) == 0
    assert len(data["recent_analyses"]) == 0


def test_dashboard_authenticated_with_data_and_isolation(client: TestClient) -> None:
    """Verify dashboard loads real persisted data for User A and strictly isolates from User B."""
    token_a = _create_user(client, "user_a_dash@example.com", "User Alpha")
    token_b = _create_user(client, "user_b_dash@example.com", "User Beta")
    headers_a = {"Authorization": f"Bearer {token_a}"}
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # 1. User A uploads policy file
    file_bytes = b"%PDF-1.4 Mock Insurance Policy Document for Alpha"
    upload_res = client.post(
        "/api/policies/upload",
        headers=headers_a,
        files={"file": ("alpha_health_shield.pdf", io.BytesIO(file_bytes), "application/pdf")},
        data={
            "insurer_name": "Max Bupa",
            "plan_name": "Health Shield Pro",
            "policy_number": "MB-SHIELD-7700",
        },
    )
    assert upload_res.status_code == 201
    policy_id = upload_res.json()["id"]

    # 2. User A runs analysis
    analysis_res = client.post(
        "/api/analyses",
        headers=headers_a,
        json={"policy_id": policy_id, "treatment_name": "Knee Replacement"},
    )
    assert analysis_res.status_code == 201

    # 3. User A runs simulation
    sim_res = client.post(
        "/api/simulations",
        headers=headers_a,
        json={"policy_id": policy_id, "hospital_quote": 350000.0, "treatment_name": "Knee Replacement"},
    )
    assert sim_res.status_code == 201

    # 4. User A checks dashboard
    dash_a = client.get("/api/dashboard", headers=headers_a)
    assert dash_a.status_code == 200
    data_a = dash_a.json()
    assert data_a["is_authenticated"] is True
    assert data_a["policies_analyzed_count"] == 1
    assert data_a["coverage_analyses_count"] == 1
    assert data_a["active_policy"] is not None
    assert data_a["active_policy"]["id"] == policy_id
    assert data_a["active_policy"]["insurer_name"] == "Max Bupa"
    assert len(data_a["recent_policies"]) == 1
    assert len(data_a["recent_analyses"]) == 1
    assert len(data_a["cost_comparison_chart"]) >= 1

    # 5. User B checks dashboard -> should have 0 policies and 0 analyses (strictly isolated!)
    dash_b = client.get("/api/dashboard", headers=headers_b)
    assert dash_b.status_code == 200
    data_b = dash_b.json()
    assert data_b["is_authenticated"] is True
    assert data_b["policies_analyzed_count"] == 0
    assert data_b["coverage_analyses_count"] == 0
    assert data_b["active_policy"] is None
    assert len(data_b["recent_policies"]) == 0
    assert len(data_b["recent_analyses"]) == 0
