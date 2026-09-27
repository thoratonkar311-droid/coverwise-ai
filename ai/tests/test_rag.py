"""Comprehensive unit and integration tests for CoverWise AI RAG subsystem.

Verifies:
- Clause-aware chunking with stable IDs and 1-indexed page references
- Lazy-loaded BGE-M3 1024-dim embedding model
- In-memory vector store operations and dimension validation
- Cross-policy isolation (preventing leakage between documents)
- Hybrid retrieval (semantic + keyword overlap)
- Grounded Q&A for:
  - Deductible ($1,500 on Page 1)
  - Coinsurance (20% on Page 2)
  - Cosmetic surgery exclusion (Page 4)
  - Prior authorization (72 hours on Page 3)
  - Unknown treatments (no hallucination)
  - Missing evidence
  - Ollama outages (graceful fallback)
"""

from pathlib import Path
from unittest import mock
import pytest

from ai.extraction.pdf_extractor import PDFExtractor
from ai.llm.client import OllamaClient
from ai.retrieval.chunking import ClauseAwareChunker
from ai.retrieval.embeddings import BGEM3EmbeddingModel, get_embedding_model
from ai.retrieval.retriever import (
    HybridPolicyRetriever,
    answer_policy_question,
    index_policy,
    retrieve_clauses,
)
from ai.retrieval.vector_store import InMemoryVectorStore


@pytest.fixture
def rag_store() -> InMemoryVectorStore:
    """Fixture providing an isolated in-memory vector store for test runs."""
    return InMemoryVectorStore(dimension=1024)


@pytest.fixture
def indexed_sample_policy(sample_pdf_path, rag_store) -> str:
    """Fixture that indexes the sample health policy PDF and returns policy ID."""
    policy_id = "test_apex_silver"
    indexed_count = index_policy(
        pdf_path=sample_pdf_path,
        policy_id=policy_id,
        vector_store=rag_store,
    )
    assert indexed_count > 0, "Expected non-zero chunks to be indexed."
    return policy_id


# -----------------------------------------------------------------------------
# 1. Chunking & Embeddings
# -----------------------------------------------------------------------------


def test_clause_aware_chunking(sample_pdf_path):
    """Verify chunker preserves clause boundaries, stable IDs, and 1-indexed pages."""
    doc = PDFExtractor().extract(sample_pdf_path)
    chunker = ClauseAwareChunker()
    chunks = chunker.chunk_document(doc)

    assert len(chunks) >= 4
    for chunk in chunks:
        assert chunk.page_number in (1, 2, 3, 4)
        assert chunk.document_id == doc.document_id
        # Verify stable ID structure: {doc_id}_p{page}_c{index}
        assert f"_p{chunk.page_number}_c" in chunk.chunk_id
        assert len(chunk.text.strip()) > 0
        assert chunk.section_title is not None


def test_bge_m3_lazy_loading_and_dimension():
    """Verify BGE-M3 model is lazy-loaded and produces strictly 1024-dim vectors."""
    model = BGEM3EmbeddingModel(force_fallback=True)
    assert model._is_loaded is False
    assert model.dimension == 1024

    # Trigger first encode
    vecs = model.encode_queries(["Annual deductible in-network"])
    assert model._is_loaded is True
    assert len(vecs) == 1
    assert len(vecs[0]) == 1024

    # Verify L2 normalization: norm should be ~1.0
    import math
    norm = math.sqrt(sum(x * x for x in vecs[0]))
    assert abs(norm - 1.0) < 1e-4


def test_invalid_vector_dimension_rejection(rag_store):
    """Verify ValueError is raised when query or document vector length != 1024."""
    with pytest.raises(ValueError) as exc_info:
        rag_store.search(query_embedding=[0.1] * 512, top_k=3)
    assert "1024" in str(exc_info.value)


# -----------------------------------------------------------------------------
# 2. Cross-Policy Isolation
# -----------------------------------------------------------------------------


def test_cross_policy_isolation(temp_pdf_factory, rag_store):
    """Verify queries on Policy A NEVER return chunks from Policy B."""
    pdf_a = temp_pdf_factory(
        ["POLICY ALPHA: Individual In-Network Deductible: $1,000."],
        filename="policy_a.pdf",
    )
    pdf_b = temp_pdf_factory(
        ["POLICY BETA: Individual In-Network Deductible: $5,000."],
        filename="policy_b.pdf",
    )

    index_policy(pdf_a, policy_id="policy_A", vector_store=rag_store)
    index_policy(pdf_b, policy_id="policy_B", vector_store=rag_store)

    # Query scoped to policy_A
    retrieved_a = retrieve_clauses("policy_A", "What is the deductible?", top_k=5, vector_store=rag_store)
    assert len(retrieved_a) > 0
    for item in retrieved_a:
        assert item.chunk.document_id == "policy_A"
        assert "1,000" in item.chunk.text
        assert "5,000" not in item.chunk.text

    # Query scoped to policy_B
    retrieved_b = retrieve_clauses("policy_B", "What is the deductible?", top_k=5, vector_store=rag_store)
    assert len(retrieved_b) > 0
    for item in retrieved_b:
        assert item.chunk.document_id == "policy_B"
        assert "5,000" in item.chunk.text
        assert "1,000" not in item.chunk.text


# -----------------------------------------------------------------------------
# 3. Grounded Q&A Requirements
# -----------------------------------------------------------------------------


def test_answer_deductible(indexed_sample_policy, rag_store):
    """Verify deductible Q&A returns $1,500 and cites Page 1."""
    res = answer_policy_question(
        policy_id=indexed_sample_policy,
        question="What is the in-network individual deductible?",
        vector_store=rag_store,
    )
    assert res["grounded"] is True
    assert "$1,500" in res["answer"]
    assert any(c["page_number"] == 1 for c in res["citations"])


def test_answer_coinsurance(indexed_sample_policy, rag_store):
    """Verify coinsurance Q&A returns 20% and cites Page 2."""
    res = answer_policy_question(
        policy_id=indexed_sample_policy,
        question="What is the in-network coinsurance rate for medical services?",
        vector_store=rag_store,
    )
    assert res["grounded"] is True
    assert "20%" in res["answer"]
    assert any(c["page_number"] == 2 for c in res["citations"])


def test_answer_cosmetic_exclusion(indexed_sample_policy, rag_store):
    """Verify cosmetic surgery exclusion Q&A states excluded and cites Page 4."""
    res = answer_policy_question(
        policy_id=indexed_sample_policy,
        question="Is cosmetic surgery covered under this policy?",
        vector_store=rag_store,
    )
    assert res["grounded"] is True
    assert "excluded" in res["answer"].lower() or "not covered" in res["answer"].lower()
    assert any(c["page_number"] == 4 for c in res["citations"])


def test_answer_prior_authorization(indexed_sample_policy, rag_store):
    """Verify prior authorization Q&A specifies 72 hours and cites Page 3."""
    res = answer_policy_question(
        policy_id=indexed_sample_policy,
        question="What are the prior authorization requirements for elective inpatient hospital stays?",
        vector_store=rag_store,
    )
    assert res["grounded"] is True
    assert "72 hours" in res["answer"].lower()
    assert any(c["page_number"] == 3 for c in res["citations"])


def test_answer_unknown_treatment_refuses_to_invent(indexed_sample_policy, rag_store):
    """Verify system does not invent coverage for unstated treatments."""
    res = answer_policy_question(
        policy_id=indexed_sample_policy,
        question="Is experimental robotic cryo-ablation for cellular regeneration covered?",
        vector_store=rag_store,
    )
    # Must refuse to hallucinate or invent coverage
    assert res["grounded"] is False
    assert len(res["citations"]) == 0
    assert "does not contain" in res["answer"].lower() or "cannot be assumed" in res["answer"].lower()


def test_missing_evidence_handling(temp_pdf_factory, rag_store):
    """Verify clean response when queried document has no relevant sections."""
    empty_doc = temp_pdf_factory(
        ["CONTACT US: Call 1-800-555-0199 for general questions."],
        filename="empty_coverage.pdf",
    )
    p_id = "sparse_doc"
    index_policy(empty_doc, policy_id=p_id, vector_store=rag_store)

    res = answer_policy_question(
        policy_id=p_id,
        question="What is the deductible for hospital stays?",
        vector_store=rag_store,
    )
    assert res["grounded"] is False
    assert len(res["citations"]) == 0


def test_ollama_outage_fallback(indexed_sample_policy, rag_store):
    """Verify answer synthesis succeeds gracefully when Ollama is offline."""
    offline_client = OllamaClient(base_url="http://127.0.0.1:59999", timeout_seconds=1)
    res = answer_policy_question(
        policy_id=indexed_sample_policy,
        question="What is the individual in-network deductible?",
        vector_store=rag_store,
        llm_client=offline_client,
    )
    assert res["grounded"] is True
    assert "$1,500" in res["answer"]
    assert len(res["citations"]) > 0
