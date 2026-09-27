"""Tests for PostgreSQL / pgvector integration interface and InMemoryVectorStore."""

import pytest
from ai.retrieval.chunking import PolicyChunk
from ai.retrieval.vector_store import (
    InMemoryVectorStore,
    PgVectorStore,
    VectorStoreError,
)


def test_pgvector_ddl_generation():
    """Verify PgVectorStore produces valid PostgreSQL / pgvector DDL statements."""
    store = PgVectorStore(
        database_url="postgresql://user:pass@localhost:5432/coverwise",
        table_name="test_policy_embeddings",
        dimension=1024,
    )
    ddl_list = store.get_ddl_statements()
    full_ddl = " ".join(ddl_list)

    assert "CREATE EXTENSION IF NOT EXISTS vector;" in full_ddl
    assert "test_policy_embeddings" in full_ddl
    assert "vector(1024)" in full_ddl
    assert "hnsw" in full_ddl.lower()
    assert "jsonb" in full_ddl.lower()


def test_in_memory_vector_store_workflow():
    """Verify InMemoryVectorStore performs accurate cosine similarity search."""
    dim = 4
    store = InMemoryVectorStore(dimension=dim)

    chunks = [
        PolicyChunk(
            chunk_id="chunk_1",
            document_id="doc_A",
            page_number=1,
            text="Annual deductible is $1500 for individual in-network.",
            section_title="Deductibles",
        ),
        PolicyChunk(
            chunk_id="chunk_2",
            document_id="doc_A",
            page_number=2,
            text="Primary care copay is $25 per visit.",
            section_title="Copays",
        ),
        PolicyChunk(
            chunk_id="chunk_3",
            document_id="doc_B",
            page_number=1,
            text="Cosmetic surgery is explicitly excluded.",
            section_title="Exclusions",
        ),
    ]

    # Orthogonal and parallel toy vectors
    embeddings = [
        [1.0, 0.0, 0.0, 0.0],
        [0.0, 1.0, 0.0, 0.0],
        [0.0, 0.0, 1.0, 0.0],
    ]

    upserted = store.upsert_chunks(chunks, embeddings)
    assert upserted == 3

    # Query most similar to chunk_1
    query_vec = [0.99, 0.05, 0.0, 0.0]
    results = store.search(query_vec, top_k=2)

    assert len(results) == 2
    top_chunk, top_score = results[0]
    assert top_chunk.chunk_id == "chunk_1"
    assert top_chunk.page_number == 1
    assert top_score > 0.95

    # Filter by document_id
    doc_b_results = store.search(query_vec, top_k=5, document_id="doc_B")
    assert len(doc_b_results) == 1
    assert doc_b_results[0][0].document_id == "doc_B"

    # Delete by document_id
    deleted = store.delete_by_document("doc_A")
    assert deleted == 2

    remaining = store.search(query_vec, top_k=5)
    assert len(remaining) == 1
    assert remaining[0][0].chunk_id == "chunk_3"

    store.close()


def test_vector_store_dimension_mismatch():
    """Verify ValueError when inserting vectors of improper dimension."""
    store = InMemoryVectorStore(dimension=1024)
    chunk = PolicyChunk(
        chunk_id="c1",
        document_id="doc1",
        page_number=1,
        text="Sample text",
    )
    with pytest.raises(ValueError):
        store.upsert_chunks([chunk], [[0.1, 0.2]])  # dimension 2 != 1024
