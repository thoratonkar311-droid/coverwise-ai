import pytest
from fastapi.testclient import TestClient

from app.models.policy import Policy
from app.db.session import SessionLocal


@pytest.fixture
def sample_test_policy() -> int:
    """Create a sample policy in the test database and return its ID."""
    db = SessionLocal()
    try:
        policy = Policy(
            filename="sample_health_policy.pdf",
            policy_number="APX-2026-TEST-001",
            insurer_name="Apex Care Assurance",
            plan_name="Apex Health Shield Silver",
            status="analyzed",
            raw_metadata={
                "deductibles": {"individual_in_network": 1500.0, "family_in_network": 3000.0},
                "coinsurance": {"in_network_percentage": 20.0},
            },
        )
        db.add(policy)
        db.commit()
        db.refresh(policy)

        from app.models.coverage_rule import CoverageRule
        from app.models.evidence_reference import EvidenceReference

        rule = CoverageRule(
            policy_id=policy.id,
            procedure_name="Total Knee Replacement",
            rule_name="Total Knee Replacement Sub-limit",
            coverage_status="covered",
            coverage_percentage=60.0,
            coverage_limit_amount=600000.0,
            waiting_period="36 months",
            source_reference="Section 3.2 (Page 7)",
        )
        db.add(rule)
        db.flush()

        ev = EvidenceReference(
            policy_id=policy.id,
            rule_id=rule.id,
            document_source=policy.filename,
            page=7,
            clause_section="Section 3.2 - Specified Procedure Sub-limits",
            extracted_text="Specified Surgeries: Total Knee Replacement covered up to 60% of sum insured, maximum Rs. 600,000.",
            interpretation="Total Knee Replacement covered up to 60% of sum insured (max 6 Lakhs).",
            confidence=0.95,
        )
        db.add(ev)
        db.commit()

        return policy.id
    finally:
        db.close()


def test_create_conversation_endpoint(client: TestClient, sample_test_policy: int) -> None:
    """Verify POST /api/conversations creates a new session."""
    payload = {
        "policy_id": sample_test_policy,
        "title": "Knee Surgery Coverage Inquiry",
        "initial_message": "Is knee replacement covered under this policy?",
    }
    res = client.post("/api/conversations", json=payload)
    assert res.status_code == 201
    data = res.json()
    assert data["policy_id"] == sample_test_policy
    assert data["title"] == "Knee Surgery Coverage Inquiry"
    assert len(data["messages"]) >= 2  # user initial message + assistant reply
    assert data["messages"][0]["role"] == "user"
    assert data["messages"][1]["role"] == "assistant"
    assert data["messages"][1]["is_grounded"] is True


def test_conversation_get_by_id(client: TestClient, sample_test_policy: int) -> None:
    """Verify GET /api/conversations/{id} retrieves complete conversation history."""
    # 1. Create
    create_res = client.post(
        "/api/conversations",
        json={"policy_id": sample_test_policy, "title": "Room Rent Question"},
    )
    assert create_res.status_code == 201
    conv_id = create_res.json()["id"]

    # 2. Get
    get_res = client.get(f"/api/conversations/{conv_id}")
    assert get_res.status_code == 200
    conv_data = get_res.json()
    assert conv_data["id"] == conv_id
    assert conv_data["policy_id"] == sample_test_policy


def test_conversation_multi_turn_context(client: TestClient, sample_test_policy: int) -> None:
    """Verify multi-turn message handling and context retention."""
    # 1. Start conversation
    create_res = client.post(
        "/api/conversations",
        json={"policy_id": sample_test_policy, "title": "Orthopedic Treatment"},
    )
    conv_id = create_res.json()["id"]

    # 2. Turn 1: Ask about procedure
    msg1_res = client.post(
        f"/api/conversations/{conv_id}/messages",
        json={"content": "Is total knee replacement covered?"},
    )
    assert msg1_res.status_code == 201
    msg1_data = msg1_res.json()
    assert msg1_data["role"] == "assistant"
    assert len(msg1_data["evidence_references"]) > 0
    assert msg1_data["evidence_references"][0]["page"] is not None

    # 3. Turn 2: Follow-up with quote without restating knee replacement
    msg2_res = client.post(
        f"/api/conversations/{conv_id}/messages",
        json={"content": "What if my hospital quote is ₹2,80,000?"},
    )
    assert msg2_res.status_code == 201
    msg2_data = msg2_res.json()
    assert msg2_data["role"] == "assistant"
    # Should detect scenario and compute deterministic estimate
    assert msg2_data["cost_estimate"] is not None
    assert msg2_data["cost_estimate"]["estimated_total_cost"] == 280000.0
    assert msg2_data["cost_estimate"]["estimated_patient_responsibility"] > 0
    assert "not insurer authorization" in msg2_data["cost_estimate"]["disclaimer"].lower()


def test_conversation_abstention_on_unknown_procedure(client: TestClient, sample_test_policy: int) -> None:
    """Verify assistant abstains and refuses to guess on unstated/unknown treatments."""
    create_res = client.post(
        "/api/conversations",
        json={"policy_id": sample_test_policy, "title": "Experimental Treatment"},
    )
    conv_id = create_res.json()["id"]

    msg_res = client.post(
        f"/api/conversations/{conv_id}/messages",
        json={"content": "Is robotic nano-cellular cryo-ablation covered?"},
    )
    assert msg_res.status_code == 201
    msg_data = msg_res.json()
    assert msg_data["is_grounded"] is False
    assert msg_data["confidence"] == "Insufficient evidence"
    assert len(msg_data["evidence_references"]) == 0
    assert "does not contain" in msg_data["content"].lower() or "cannot be assumed" in msg_data["content"].lower()


def test_conversation_policy_listing(client: TestClient, sample_test_policy: int) -> None:
    """Verify listing conversations by policy ID."""
    res = client.get(f"/api/conversations/policy/{sample_test_policy}")
    assert res.status_code == 200
    assert isinstance(res.json(), list)
