"""Retrieval and vector search module for CoverWise AI.

Provides clause-aware chunking, lazy-loaded BGE-M3 (1024-dim) embeddings,
in-memory vector storage, pgvector interface, hybrid retrieval, and grounded Q&A.
"""

from ai.retrieval.chunking import (
    ClauseAwareChunker,
    PolicyChunk,
    PolicyChunkerInterface,
)
from ai.retrieval.embeddings import (
    BGEM3EmbeddingModel,
    EmbeddingModelInterface,
    get_embedding_model,
)
from ai.retrieval.retriever import (
    HybridPolicyRetriever,
    PolicyQAResponse,
    PolicyRetrieverInterface,
    RetrievedChunk,
    answer_policy_question,
    get_default_vector_store,
    index_policy,
    retrieve_clauses,
)
from ai.retrieval.vector_store import (
    InMemoryVectorStore,
    PgVectorStore,
    VectorStoreError,
    VectorStoreInterface,
)

__all__ = [
    "ClauseAwareChunker",
    "PolicyChunk",
    "PolicyChunkerInterface",
    "BGEM3EmbeddingModel",
    "EmbeddingModelInterface",
    "get_embedding_model",
    "HybridPolicyRetriever",
    "PolicyQAResponse",
    "PolicyRetrieverInterface",
    "RetrievedChunk",
    "InMemoryVectorStore",
    "PgVectorStore",
    "VectorStoreError",
    "VectorStoreInterface",
    "get_default_vector_store",
    "index_policy",
    "retrieve_clauses",
    "answer_policy_question",
]
