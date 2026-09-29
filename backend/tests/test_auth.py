from fastapi.testclient import TestClient


def test_register_user_success(client: TestClient) -> None:
    """Verify successful user registration returns JWT token and sanitized user profile."""
    payload = {
        "email": "dr.smith@example.com",
        "password": "SecurePassword123!",
        "full_name": "Dr. John Smith",
    }
    response = client.post("/api/auth/register", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert "user" in data
    user = data["user"]
    assert user["email"] == "dr.smith@example.com"
    assert user["full_name"] == "Dr. John Smith"
    assert user["is_active"] is True
    assert "password" not in user
    assert "password_hash" not in user


def test_register_duplicate_email(client: TestClient) -> None:
    """Verify registering an existing email returns 400 Bad Request."""
    payload = {
        "email": "duplicate.user@example.com",
        "password": "Password123!",
        "full_name": "Duplicate User",
    }
    first_res = client.post("/api/auth/register", json=payload)
    assert first_res.status_code == 201

    second_res = client.post("/api/auth/register", json=payload)
    assert second_res.status_code == 400
    detail = second_res.json()["detail"]
    assert "already exists" in detail.lower()


def test_login_success(client: TestClient) -> None:
    """Verify login with valid credentials returns access token."""
    email = "login.success@example.com"
    password = "CorrectPassword456!"
    client.post(
        "/api/auth/register",
        json={"email": email, "password": password, "full_name": "Login User"},
    )

    response = client.post(
        "/api/auth/login",
        json={"email": email, "password": password},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == email


def test_login_wrong_password(client: TestClient) -> None:
    """Verify login fails with 401 when password does not match."""
    email = "wrong.pass@example.com"
    client.post(
        "/api/auth/register",
        json={"email": email, "password": "OriginalPassword1!", "full_name": "Test User"},
    )

    response = client.post(
        "/api/auth/login",
        json={"email": email, "password": "IncorrectPassword999!"},
    )
    assert response.status_code == 401
    assert "invalid email or password" in response.json()["detail"].lower()


def test_login_nonexistent_email(client: TestClient) -> None:
    """Verify login fails with 401 for unknown email address."""
    response = client.post(
        "/api/auth/login",
        json={"email": "nobody_here_999@example.com", "password": "AnyPassword!"},
    )
    assert response.status_code == 401
    assert "invalid email or password" in response.json()["detail"].lower()


def test_get_current_user_me(client: TestClient) -> None:
    """Verify /api/auth/me returns current user identity with valid Bearer token."""
    email = "me.profile@example.com"
    reg_res = client.post(
        "/api/auth/register",
        json={"email": email, "password": "ValidPassword99!", "full_name": "Me User"},
    )
    token = reg_res.json()["access_token"]

    response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    profile = response.json()
    assert profile["email"] == email
    assert profile["full_name"] == "Me User"
    assert "password_hash" not in profile


def test_get_current_user_invalid_or_missing_token(client: TestClient) -> None:
    """Verify /api/auth/me returns 401 for invalid or missing authentication headers."""
    # Missing token
    res_no_auth = client.get("/api/auth/me")
    assert res_no_auth.status_code == 401

    # Invalid token format
    res_bad_token = client.get(
        "/api/auth/me",
        headers={"Authorization": "Bearer totally-invalid-jwt-token-string"},
    )
    assert res_bad_token.status_code == 401


def test_logout(client: TestClient) -> None:
    """Verify /api/auth/logout acknowledges session termination."""
    email = "logout.test@example.com"
    reg_res = client.post(
        "/api/auth/register",
        json={"email": email, "password": "PasswordToLogout1!", "full_name": "Logout User"},
    )
    token = reg_res.json()["access_token"]

    response = client.post(
        "/api/auth/logout",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert "logged out" in response.json()["message"].lower()
