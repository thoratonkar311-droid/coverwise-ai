import io
from fastapi.testclient import TestClient


def _create_user_and_token(client: TestClient, email: str, name: str) -> str:
    """Helper to register a user and return the JWT bearer token."""
    res = client.post(
        "/api/auth/register",
        json={"email": email, "password": "SecurePassword123!", "full_name": name},
    )
    assert res.status_code == 201
    return res.json()["access_token"]


def test_policy_idor_isolation(client: TestClient) -> None:
    """Verify that User B cannot access, update, or delete User A's policy."""
    token_a = _create_user_and_token(client, "user_a_policy@example.com", "User A")
    token_b = _create_user_and_token(client, "user_b_policy@example.com", "User B")

    # 1. User A uploads/creates policy
    headers_a = {"Authorization": f"Bearer {token_a}"}
    headers_b = {"Authorization": f"Bearer {token_b}"}

    create_res = client.post(
        "/api/policies",
        headers=headers_a,
        json={
            "filename": "user_a_health_plan.pdf",
            "insurer_name": "Religare Health",
            "policy_number": "REL-POL-1001",
        },
    )
    assert create_res.status_code == 201
    policy_id = create_res.json()["id"]

    # 2. User A can view own policy
    res_owner = client.get(f"/api/policies/{policy_id}", headers=headers_a)
    assert res_owner.status_code == 200
    assert res_owner.json()["id"] == policy_id

    # 3. User B receives 403 Forbidden attempting to access User A's policy
    res_other = client.get(f"/api/policies/{policy_id}", headers=headers_b)
    assert res_other.status_code == 403
    assert "permission" in res_other.json()["detail"].lower()

    # 4. Unauthenticated user receives 401 Unauthorized
    res_unauth = client.get(f"/api/policies/{policy_id}")
    assert res_unauth.status_code == 401

    # 5. User B cannot update User A's policy
    res_patch = client.patch(
        f"/api/policies/{policy_id}",
        headers=headers_b,
        json={"notes": "Hacked notes"},
    )
    assert res_patch.status_code == 403

    # 6. User B cannot delete User A's policy
    res_del = client.delete(f"/api/policies/{policy_id}", headers=headers_b)
    assert res_del.status_code == 403


def test_analysis_idor_isolation(client: TestClient) -> None:
    """Verify that User B cannot run analysis on or view User A's policy analysis."""
    token_a = _create_user_and_token(client, "user_a_analysis@example.com", "User A")
    token_b = _create_user_and_token(client, "user_b_analysis@example.com", "User B")
    headers_a = {"Authorization": f"Bearer {token_a}"}
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # User A creates policy
    p_res = client.post(
        "/api/policies",
        headers=headers_a,
        json={"filename": "a_policy.pdf", "insurer_name": "Star Health"},
    )
    policy_id = p_res.json()["id"]

    # User A runs analysis
    analysis_res = client.post(
        "/api/analyses",
        headers=headers_a,
        json={"policy_id": policy_id, "treatment_name": "Cardiac Angioplasty"},
    )
    assert analysis_res.status_code == 201
    analysis_id = analysis_res.json()["id"]

    # User A can fetch analysis
    fetch_a = client.get(f"/api/analyses/{analysis_id}", headers=headers_a)
    assert fetch_a.status_code == 200

    # User B cannot fetch User A's analysis (403)
    fetch_b = client.get(f"/api/analyses/{analysis_id}", headers=headers_b)
    assert fetch_b.status_code == 403

    # User B cannot trigger new analysis on User A's policy (403)
    run_b = client.post(
        "/api/analyses",
        headers=headers_b,
        json={"policy_id": policy_id, "treatment_name": "Chemotherapy"},
    )
    assert run_b.status_code == 403


def test_conversation_idor_isolation(client: TestClient) -> None:
    """Verify that User B cannot access or message User A's policy conversation."""
    token_a = _create_user_and_token(client, "user_a_conv@example.com", "User A")
    token_b = _create_user_and_token(client, "user_b_conv@example.com", "User B")
    headers_a = {"Authorization": f"Bearer {token_a}"}
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # User A creates policy
    p_res = client.post(
        "/api/policies",
        headers=headers_a,
        json={"filename": "conv_policy.pdf", "insurer_name": "Niva Bupa"},
    )
    policy_id = p_res.json()["id"]

    # User B cannot start conversation on User A's policy (403)
    start_b = client.post(
        "/api/conversations",
        headers=headers_b,
        json={"policy_id": policy_id, "title": "B's conversation on A's policy"},
    )
    assert start_b.status_code == 403

    # User A starts conversation
    start_a = client.post(
        "/api/conversations",
        headers=headers_a,
        json={"policy_id": policy_id, "title": "A's policy questions"},
    )
    assert start_a.status_code == 201
    conv_id = start_a.json()["id"]

    # User B cannot fetch User A's conversation (403)
    fetch_b = client.get(f"/api/conversations/{conv_id}", headers=headers_b)
    assert fetch_b.status_code == 403

    # User B cannot post message to User A's conversation (403)
    msg_b = client.post(
        f"/api/conversations/{conv_id}/messages",
        headers=headers_b,
        json={"content": "Injecting unauthorized message"},
    )
    assert msg_b.status_code == 403


def test_simulation_idor_isolation(client: TestClient) -> None:
    """Verify that User B cannot run simulation on or view User A's simulations."""
    token_a = _create_user_and_token(client, "user_a_sim@example.com", "User A")
    token_b = _create_user_and_token(client, "user_b_sim@example.com", "User B")
    headers_a = {"Authorization": f"Bearer {token_a}"}
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # User A creates policy
    p_res = client.post(
        "/api/policies",
        headers=headers_a,
        json={"filename": "sim_policy.pdf", "insurer_name": "Bajaj Allianz"},
    )
    policy_id = p_res.json()["id"]

    # User B cannot run simulation against User A's policy (403)
    sim_b = client.post(
        "/api/simulations",
        headers=headers_b,
        json={"policy_id": policy_id, "hospital_quote": 250000.0, "treatment_name": "Appendectomy"},
    )
    assert sim_b.status_code == 403

    # User A runs simulation
    sim_a = client.post(
        "/api/simulations",
        headers=headers_a,
        json={"policy_id": policy_id, "hospital_quote": 250000.0, "treatment_name": "Appendectomy"},
    )
    assert sim_a.status_code == 201
    sim_id = sim_a.json()["id"]

    # User B cannot get User A's simulation record (403)
    get_sim_b = client.get(f"/api/simulations/{sim_id}", headers=headers_b)
    assert get_sim_b.status_code == 403
