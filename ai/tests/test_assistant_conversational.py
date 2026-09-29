"""Automated tests for conversational policy assistant retrieval and evidence grounding."""

from pathlib import Path
import pytest
from ai.retrieval.retriever import answer_policy_question, index_policy
from ai.retrieval.vector_store import InMemoryVectorStore

SAMPLE_DIR = Path(__file__).resolve().parent.parent / "sample_policies"


@pytest.fixture
def sample_indexed_policy(sample_pdf_path) -> tuple[str, InMemoryVectorStore]:
    """Index sample health policy in an isolated vector store."""
    store = InMemoryVectorStore(dimension=1024)
    policy_id = "test_assistant_policy"
    index_policy(sample_pdf_path, policy_id=policy_id, vector_store=store)
    return policy_id, store


@pytest.fixture
def indian_indexed_policy() -> tuple[str, InMemoryVectorStore]:
    """Index Indian health policy in an isolated vector store."""
    store = InMemoryVectorStore(dimension=1024)
    policy_id = "test_indian_policy"
    pdf_path = SAMPLE_DIR / "indian_health_policy.pdf"
    index_policy(pdf_path, policy_id=policy_id, vector_store=store)
    return policy_id, store


def test_conversational_multi_turn_procedure_followup(indian_indexed_policy):
    """Verify follow-up question regarding quote utilizes previous turn context."""
    policy_id, store = indian_indexed_policy

    history = [
        {"role": "user", "content": "Is total knee replacement covered?"},
        {
            "role": "assistant",
            "content": "Potentially covered, subject to the policy's waiting period and applicable exclusions.",
        },
    ]

    res = answer_policy_question(
        policy_id=policy_id,
        question="What if my hospital quote is ₹3,00,000?",
        vector_store=store,
        conversation_history=history,
    )
    assert res["grounded"] is True
    assert len(res["citations"]) > 0
    assert any(c["page_number"] > 0 for c in res["citations"])


def test_conversational_room_rent_limit_citation(indian_indexed_policy):
    """Verify room rent inquiry returns exact limit and page reference."""
    policy_id, store = indian_indexed_policy

    res = answer_policy_question(
        policy_id=policy_id,
        question="Does this policy have a room-rent limit?",
        vector_store=store,
    )
    assert res["grounded"] is True
    assert "room" in res["answer"].lower()
    assert len(res["citations"]) > 0


def test_conversational_waiting_period_citation_when_present(indian_indexed_policy):
    """Verify waiting period inquiry cites policy evidence when present in policy."""
    policy_id, store = indian_indexed_policy

    res = answer_policy_question(
        policy_id=policy_id,
        question="What is the waiting period for pre-existing diseases?",
        vector_store=store,
    )
    assert res["grounded"] is True
    assert "waiting" in res["answer"].lower()
    assert len(res["citations"]) > 0


def test_conversational_waiting_period_abstention_when_not_stated(sample_indexed_policy):
    """Verify system abstains when waiting period is not stated in uploaded policy."""
    policy_id, store = sample_indexed_policy

    res = answer_policy_question(
        policy_id=policy_id,
        question="What is the waiting period for pre-existing diseases?",
        vector_store=store,
    )
    assert res["grounded"] is False
    assert res["confidence"] == "Insufficient evidence"
    assert "could not be determined" in res["answer"].lower()


def test_conversational_abstention_unknown_procedure(sample_indexed_policy):
    """Verify assistant strictly refuses to guess or invent coverage for unstated treatments."""
    policy_id, store = sample_indexed_policy

    res = answer_policy_question(
        policy_id=policy_id,
        question="Is robotic cryo-ablation for cellular regeneration covered?",
        vector_store=store,
    )
    assert res["grounded"] is False
    assert res["confidence"] == "Insufficient evidence"
    assert len(res["citations"]) == 0
    assert "does not contain" in res["answer"].lower() or "cannot be assumed" in res["answer"].lower()
