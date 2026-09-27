import io
from fastapi.testclient import TestClient


def test_create_and_get_policy(client: TestClient) -> None:
    """Verify policy creation via JSON payload and subsequent retrieval."""
    payload = {
        "filename": "star_health_optima.pdf",
        "policy_number": "POL-2024-9988",
        "insurer_name": "Star Health",
        "plan_name": "Family Optima",
        "policy_holder_name": "John Doe",
        "status": "uploaded",
    }
    response = client.post("/api/policies", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["id"] is not None
    assert data["filename"] == "star_health_optima.pdf"
    assert data["insurer_name"] == "Star Health"
    policy_id = data["id"]

    # Fetch policy
    get_res = client.get(f"/api/policies/{policy_id}")
    assert get_res.status_code == 200
    get_data = get_res.json()
    assert get_data["id"] == policy_id
    assert get_data["policy_number"] == "POL-2024-9988"


def test_list_policies(client: TestClient) -> None:
    """Verify listing policies returns list with pagination."""
    response = client.get("/api/policies?skip=0&limit=10")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1


def test_upload_policy_file(client: TestClient) -> None:
    """Verify policy file upload with multipart form-data."""
    file_content = b"%PDF-1.4 Mock Policy Document for Testing"
    file_obj = io.BytesIO(file_content)

    response = client.post(
        "/api/policies/upload",
        files={"file": ("hdfc_ergo_health.pdf", file_obj, "application/pdf")},
        data={
            "insurer_name": "HDFC ERGO",
            "plan_name": "Optima Restore",
            "policy_number": "HDFC-882233",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["id"] is not None
    assert data["filename"] == "hdfc_ergo_health.pdf"
    assert data["status"] == "uploaded"


def test_upload_policy_unsupported_format(client: TestClient) -> None:
    """Verify upload rejects unsupported file extensions with 415 Unsupported Media Type."""
    file_content = b"Binary executable content"
    file_obj = io.BytesIO(file_content)

    response = client.post(
        "/api/policies/upload",
        files={"file": ("malicious_payload.exe", file_obj, "application/octet-stream")},
    )
    assert response.status_code == 415
    data = response.json()
    assert "error" in data
    assert "Unsupported file format" in data["error"]["message"]


def test_upload_policy_empty_file(client: TestClient) -> None:
    """Verify upload rejects empty (0 byte) files with 400 Bad Request."""
    empty_file = io.BytesIO(b"")
    response = client.post(
        "/api/policies/upload",
        files={"file": ("empty_policy.pdf", empty_file, "application/pdf")},
    )
    assert response.status_code == 400
    data = response.json()
    assert "error" in data
    assert "empty" in data["error"]["message"]


def test_upload_policy_oversized_file(client: TestClient, monkeypatch) -> None:
    """Verify upload enforces file size limit and returns 413 Payload Too Large."""
    # Monkeypatch MAX_FILE_SIZE_BYTES to 1KB to test size limitation quickly
    import app.api.routes.policies as policies_module

    monkeypatch.setattr(policies_module, "MAX_FILE_SIZE_BYTES", 1024)

    oversized_content = b"X" * 2048  # 2KB > 1KB
    file_obj = io.BytesIO(oversized_content)

    response = client.post(
        "/api/policies/upload",
        files={"file": ("large_policy.pdf", file_obj, "application/pdf")},
    )
    assert response.status_code == 413
    data = response.json()
    assert "error" in data
    assert "File size exceeds" in data["error"]["message"]


def test_policy_path_gt_zero_validation(client: TestClient) -> None:
    """Verify path parameter validation rejects policy_id <= 0 with 422."""
    res = client.get("/api/policies/0")
    assert res.status_code == 422

    res_neg = client.get("/api/policies/-5")
    assert res_neg.status_code == 422


def test_update_and_delete_policy(client: TestClient) -> None:
    """Verify partial update and deletion of policy."""
    create_res = client.post(
        "/api/policies",
        json={"filename": "temp_delete_test.pdf", "insurer_name": "To Delete"},
    )
    policy_id = create_res.json()["id"]

    # Patch update
    update_res = client.patch(
        f"/api/policies/{policy_id}",
        json={"plan_name": "Updated Plan", "status": "processed"},
    )
    assert update_res.status_code == 200
    assert update_res.json()["plan_name"] == "Updated Plan"
    assert update_res.json()["status"] == "processed"

    # Delete
    del_res = client.delete(f"/api/policies/{policy_id}")
    assert del_res.status_code == 200
    assert del_res.json()["id"] == policy_id

    # Verify 404 after deletion
    verify_res = client.get(f"/api/policies/{policy_id}")
    assert verify_res.status_code == 404
