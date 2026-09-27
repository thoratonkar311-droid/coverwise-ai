from fastapi.testclient import TestClient


def test_list_and_seed_treatments(client: TestClient) -> None:
    """Verify treatments catalog lists standard seeded procedures."""
    response = client.get("/api/treatments")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 5

    names = [item["name"] for item in data]
    assert any("Cataract" in name for name in names)
    assert any("Knee" in name for name in names)


def test_get_treatment_by_id(client: TestClient) -> None:
    """Verify fetching single treatment by ID."""
    list_res = client.get("/api/treatments")
    first_item = list_res.json()[0]
    treatment_id = first_item["id"]

    res = client.get(f"/api/treatments/{treatment_id}")
    assert res.status_code == 200
    assert res.json()["id"] == treatment_id
    assert res.json()["name"] == first_item["name"]


def test_search_treatments(client: TestClient) -> None:
    """Verify filtering and querying treatments by name or category."""
    # Search query
    res = client.get("/api/treatments?q=cataract")
    assert res.status_code == 200
    results = res.json()
    assert len(results) >= 1
    assert "Cataract" in results[0]["name"]

    # Category filter
    res_cat = client.get("/api/treatments?category=Cardiology")
    assert res_cat.status_code == 200
    assert all(item["category"] == "Cardiology" for item in res_cat.json())


def test_create_treatment_and_conflict(client: TestClient) -> None:
    """Verify creating a new treatment and conflict detection on duplicate name."""
    payload = {
        "name": "Robotic Prostatectomy",
        "category": "Urology",
        "description": "Minimally invasive da Vinci robotic surgical resection.",
        "typical_cost_min": 250000.0,
        "typical_cost_max": 450000.0,
    }
    create_res = client.post("/api/treatments", json=payload)
    assert create_res.status_code == 201
    assert create_res.json()["name"] == "Robotic Prostatectomy"

    # Duplicate should return 409
    dup_res = client.post("/api/treatments", json=payload)
    assert dup_res.status_code == 409
