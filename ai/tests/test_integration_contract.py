"""Integration tests for CoverWise AI Member 2/Member 3 contract.

Tests:
1. Validated Pydantic request & response interfaces.
2. End-to-end AIService operations (extract, index, retrieve, ask, health).
3. Duplicate indexing prevention via cryptographic hash checks.
4. Cross-user multi-tenant policy isolation.
5. Unsafe PDF upload defense (path traversal, invalid headers, empty files).
6. Sensitive data scrubbing and log redaction.
7. Database connectivity probe with graceful in-memory fallback.
8. Mock FastAPI backend integration workflows.
"""

import logging
from pathlib import Path
import tempfile
import pytest

from ai.config import get_settings
from ai.integration.models import (
    AIHealthCheckResponse,
    ClauseRetrieveRequest,
    ClauseRetrieveResponse,
    PolicyExtractRequest,
    PolicyExtractResponse,
    PolicyIndexRequest,
    PolicyIndexResponse,
    PolicyQuestionRequest,
    PolicyQuestionResponse,
)
from ai.integration.security import (
    InvalidPDFError,
    SensitiveDataFilter,
    UnsafeUploadError,
    mask_sensitive_phi,
    validate_pdf_file,
)
from ai.integration.service import AIService, get_ai_service
from ai.retrieval.chunking import PolicyChunk
from ai.retrieval.vector_store import InMemoryVectorStore, check_database_connectivity


@pytest.fixture
def sample_pdf_path() -> Path:
    """Return verified path to sample policy PDF."""
    path = Path(__file__).resolve().parent.parent / "sample_policies" / "sample_health_policy.pdf"
    assert path.exists(), f"Sample policy fixture not found at {path}"
    return path


@pytest.fixture
def isolated_ai_service() -> AIService:
    """Return an AIService instance with an isolated in-memory vector store."""
    store = InMemoryVectorStore(dimension=1024)
    return AIService(vector_store=store)


# ==============================================================================
# 1. Pydantic Interface & Validation Tests
# ==============================================================================

def test_integration_models_validation():
    """Verify request and response models strictly validate inputs."""
    # Invalid empty fields
    with pytest.raises(Exception):
        PolicyExtractRequest(pdf_path="")

    with pytest.raises(Exception):
        ClauseRetrieveRequest(policy_id="", query="")

    with pytest.raises(Exception):
        ClauseRetrieveRequest(policy_id="APX", query="test", top_k=50)  # top_k > 20

    with pytest.raises(Exception):
        PolicyQuestionRequest(policy_id="", question="x")  # question min_length=2

    req = PolicyQuestionRequest(policy_id="POL-123", question="What is deductible?", user_id="usr_99")
    assert req.policy_id == "POL-123"
    assert req.user_id == "usr_99"


# ==============================================================================
# 2. End-to-End AIService Extraction Tests
# ==============================================================================

def test_ai_service_extract_policy(isolated_ai_service: AIService, sample_pdf_path: Path):
    """Verify AIService extraction preserves exact page citations and warnings."""
    req = PolicyExtractRequest(pdf_path=str(sample_pdf_path), user_id="user_123")
    resp = isolated_ai_service.extract_policy(req)

    assert isinstance(resp, PolicyExtractResponse)
    assert resp.status == "success"
    assert resp.execution_time_ms >= 0.0

    # Policy attributes
    assert resp.policy.metadata.policy_id == "APX-2026-SLV-9012"
    assert resp.policy.deductibles.individual_in_network == 1500.00
    assert resp.policy.coinsurance.in_network_percentage == 20.0
    assert len(resp.policy.exclusions) >= 6

    # Verify audit warnings are captured
    assert len(resp.warnings) > 0
    assert any("prior authorization" in w.lower() for w in resp.warnings)


# ==============================================================================
# 3. Duplicate Indexing Prevention Tests
# ==============================================================================

def test_ai_service_duplicate_indexing_prevention(isolated_ai_service: AIService, sample_pdf_path: Path):
    """Verify re-indexing the identical PDF is skipped via SHA-256 content hash."""
    req = PolicyIndexRequest(
        pdf_path=str(sample_pdf_path),
        policy_id="TEST-DUP-POLICY",
        user_id="user_tenant_1",
    )

    # Initial indexing
    resp1 = isolated_ai_service.index_policy(req)
    assert resp1.status == "indexed"
    assert resp1.is_duplicate is False
    assert resp1.indexed_chunks == 4
    assert len(resp1.content_hash) == 64

    # Second indexing of same file should detect duplicate and skip re-embedding
    resp2 = isolated_ai_service.index_policy(req)
    assert resp2.status == "already_indexed"
    assert resp2.is_duplicate is True
    assert resp2.indexed_chunks == 4
    assert resp2.content_hash == resp1.content_hash
    assert any("duplicate" in w.lower() for w in resp2.warnings)

    # Force reindex should bypass duplicate check
    force_req = PolicyIndexRequest(
        pdf_path=str(sample_pdf_path),
        policy_id="TEST-DUP-POLICY",
        user_id="user_tenant_1",
        force_reindex=True,
    )
    resp3 = isolated_ai_service.index_policy(force_req)
    assert resp3.status == "indexed"
    assert resp3.is_duplicate is False


# ==============================================================================
# 4. Multi-Tenant Cross-User Isolation Tests
# ==============================================================================

def test_ai_service_cross_user_tenant_isolation(isolated_ai_service: AIService, sample_pdf_path: Path):
    """Verify User B cannot retrieve or access policies indexed by User A."""
    # User A indexes their policy
    index_req_a = PolicyIndexRequest(
        pdf_path=str(sample_pdf_path),
        policy_id="CONFIDENTIAL-POLICY-A",
        user_id="user_alice",
    )
    isolated_ai_service.index_policy(index_req_a)

    # User B queries User A's policy
    query_b = ClauseRetrieveRequest(
        policy_id="CONFIDENTIAL-POLICY-A",
        query="deductible",
        user_id="user_bob",
    )
    resp_b = isolated_ai_service.retrieve_clauses(query_b)
    # User B MUST see 0 matches
    assert resp_b.matches_count == 0
    assert len(resp_b.clauses) == 0

    # User A queries their own policy
    query_a = ClauseRetrieveRequest(
        policy_id="CONFIDENTIAL-POLICY-A",
        query="deductible",
        user_id="user_alice",
    )
    resp_a = isolated_ai_service.retrieve_clauses(query_a)
    assert resp_a.matches_count > 0
    assert "deductible" in resp_a.clauses[0].text.lower()


# ==============================================================================
# 5. Grounded Q&A Status & Warnings Tests
# ==============================================================================

def test_ai_service_answer_question_reporting(isolated_ai_service: AIService, sample_pdf_path: Path):
    """Verify answer_question reports live-vs-fallback status and exact page citations."""
    # Index first
    isolated_ai_service.index_policy(
        PolicyIndexRequest(pdf_path=str(sample_pdf_path), policy_id="APEX-QA", user_id="usr_1")
    )

    # Ask deductible question
    q_req = PolicyQuestionRequest(policy_id="APEX-QA", question="What is the in-network deductible?", user_id="usr_1")
    resp = isolated_ai_service.answer_question(q_req)

    assert isinstance(resp, PolicyQuestionResponse)
    assert resp.grounded is True
    assert "1,500" in resp.answer
    assert resp.retrieved_clauses_count > 0
    assert len(resp.citations) > 0
    assert resp.citations[0].page_number >= 1

    # Status tracking fields
    assert isinstance(resp.is_live_model, bool)
    assert isinstance(resp.fallback_used, bool)
    assert len(resp.model_name) > 0

    # Test unknown treatment refusal
    q_unknown = PolicyQuestionRequest(policy_id="APEX-QA", question="Is robotic limb replacement covered?", user_id="usr_1")
    resp_unknown = isolated_ai_service.answer_question(q_unknown)
    assert resp_unknown.grounded is False
    assert len(resp_unknown.citations) == 0
    assert "does not contain" in resp_unknown.answer.lower()
    assert len(resp_unknown.warnings) > 0


# ==============================================================================
# 6. Unsafe PDF Upload Defense Tests
# ==============================================================================

def test_unsafe_pdf_upload_rejection():
    """Verify rejection of path traversal, invalid headers, wrong extensions, and empty files."""
    # 1. Path traversal attempt
    with pytest.raises(UnsafeUploadError):
        validate_pdf_file("../../secret/policy.pdf")

    # 2. Non-existent file
    with pytest.raises(InvalidPDFError):
        validate_pdf_file("non_existent_policy.pdf")

    # 3. Wrong extension
    with tempfile.NamedTemporaryFile(suffix=".exe", delete=False) as tmp:
        tmp.write(b"BINARY_PAYLOAD")
        tmp_name = tmp.name

    try:
        with pytest.raises(InvalidPDFError):
            validate_pdf_file(tmp_name)
    finally:
        Path(tmp_name).unlink(missing_ok=True)

    # 4. Invalid header (wrong magic bytes)
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(b"NOT_A_VALID_PDF_HEADER")
        tmp_name = tmp.name

    try:
        with pytest.raises(InvalidPDFError):
            validate_pdf_file(tmp_name)
    finally:
        Path(tmp_name).unlink(missing_ok=True)

    # 5. Empty file (0 bytes)
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp_name = tmp.name

    try:
        with pytest.raises(InvalidPDFError):
            validate_pdf_file(tmp_name)
    finally:
        Path(tmp_name).unlink(missing_ok=True)


# ==============================================================================
# 7. Sensitive Data Redaction Tests
# ==============================================================================

def test_sensitive_phi_redaction():
    """Verify SSN, phone, email, card, and bearer tokens are masked."""
    sample_text = (
        "Patient SSN: 123-45-6789, Phone: (555) 123-4567. "
        "Contact patient@example.com with Card: 4111-2222-3333-4444. "
        "Authorization: Bearer secret_token_xyz123"
    )
    cleaned = mask_sensitive_phi(sample_text)

    assert "123-45-6789" not in cleaned
    assert "[REDACTED_SSN]" in cleaned
    assert "4111-2222-3333-4444" not in cleaned
    assert "[REDACTED_CARD]" in cleaned
    assert "patient@example.com" not in cleaned
    assert "[REDACTED_EMAIL]" in cleaned
    assert "secret_token_xyz123" not in cleaned
    assert "Bearer [REDACTED_TOKEN]" in cleaned


def test_sensitive_logging_filter():
    """Verify SensitiveDataFilter intercepts and cleans sensitive logging records."""
    fil = SensitiveDataFilter()
    record = logging.LogRecord(
        name="coverwise_ai.test",
        level=logging.INFO,
        pathname=__file__,
        lineno=10,
        msg="Processing claim for SSN 999-88-7777 and email test@test.org",
        args=(),
        exc_info=None,
    )
    fil.filter(record)

    assert "999-88-7777" not in record.msg
    assert "[REDACTED_SSN]" in record.msg
    assert "test@test.org" not in record.msg
    assert "[REDACTED_EMAIL]" in record.msg


# ==============================================================================
# 8. Database Probe & In-Memory Fallback Tests
# ==============================================================================

def test_database_connectivity_fallback():
    """Verify database connectivity probe gracefully retains InMemoryVectorStore fallback."""
    # When DATABASE_URL is None
    connected, diag = check_database_connectivity(None)
    assert connected is False
    assert "InMemoryVectorStore" in diag

    # When DATABASE_URL points to non-existent unreachable host
    connected, diag = check_database_connectivity("postgresql://fakeuser:fakepass@127.0.0.1:59999/fakedb")
    assert connected is False
    assert "unreachable" in diag.lower() or "failed" in diag.lower() or "inmemory" in diag.lower()


def test_ai_service_health_check(isolated_ai_service: AIService):
    """Verify AIService.check_health returns complete diagnostic status."""
    health = isolated_ai_service.check_health()
    assert isinstance(health, AIHealthCheckResponse)
    assert health.status in ("healthy", "degraded")
    assert health.database_type in ("in_memory", "postgres")
    assert health.embedding_dimension == 1024
    assert len(health.llm_model) > 0


# ==============================================================================
# 9. Mock FastAPI Backend Integration Flow
# ==============================================================================

def test_mock_fastapi_backend_integration(isolated_ai_service: AIService, sample_pdf_path: Path):
    """Simulate Member 2's FastAPI endpoints calling the AI integration service."""
    # Step 1: Member 2 POST /api/policies/extract
    extract_req = PolicyExtractRequest(pdf_path=str(sample_pdf_path), user_id="member2_client")
    extract_resp = isolated_ai_service.extract_policy(extract_req)
    assert extract_resp.status == "success"
    # Ensure serializable to JSON dictionary (for FastAPI response)
    json_dict = extract_resp.model_dump()
    assert "policy" in json_dict

    # Step 2: Member 2 POST /api/policies/index
    index_req = PolicyIndexRequest(
        pdf_path=str(sample_pdf_path),
        policy_id="FASTAPI-POLICY-01",
        user_id="member2_client",
    )
    index_resp = isolated_ai_service.index_policy(index_req)
    assert index_resp.status == "indexed"
    assert index_resp.indexed_chunks > 0

    # Step 3: Member 2 POST /api/policies/search
    search_req = ClauseRetrieveRequest(
        policy_id="FASTAPI-POLICY-01",
        query="outpatient surgery coinsurance",
        user_id="member2_client",
        top_k=3,
    )
    search_resp = isolated_ai_service.retrieve_clauses(search_req)
    assert search_resp.matches_count > 0

    # Step 4: Member 2 POST /api/policies/ask
    qa_req = PolicyQuestionRequest(
        policy_id="FASTAPI-POLICY-01",
        question="What is the coinsurance for outpatient surgery?",
        user_id="member2_client",
    )
    qa_resp = isolated_ai_service.answer_question(qa_req)
    assert qa_resp.grounded is True
    assert len(qa_resp.citations) > 0
