"""Validated Pydantic v2 schemas defining the FastAPI integration contract.

Exposes request and response contracts for Member 2's backend:
- Structured policy extraction
- Policy indexing and deduplication
- Clause retrieval with hybrid search
- Grounded policy Q&A with live-model-vs-fallback reporting
- AI health and database diagnostics
"""

from typing import Any
from pydantic import BaseModel, ConfigDict, Field

from ai.schemas.evidence import Citation
from ai.schemas.policy import PolicyAnalysis


class PolicyExtractRequest(BaseModel):
    """Request contract for extracting structured policy data from a PDF."""

    model_config = ConfigDict(frozen=True)

    pdf_path: str = Field(..., min_length=1, description="File path to the policy PDF.")
    user_id: str | None = Field(default=None, description="Optional tenant or user identifier.")


class PolicyExtractResponse(BaseModel):
    """Response contract for structured policy extraction."""

    model_config = ConfigDict(frozen=True)

    status: str = Field(default="success", description="Execution status ('success' or 'error').")
    policy: PolicyAnalysis = Field(..., description="Validated structured policy intelligence.")
    execution_time_ms: float = Field(..., ge=0.0, description="Extraction duration in milliseconds.")
    warnings: list[str] = Field(default_factory=list, description="Audit warnings or caveats.")


class PolicyIndexRequest(BaseModel):
    """Request contract for indexing a policy PDF into the vector store."""

    model_config = ConfigDict(frozen=True)

    pdf_path: str = Field(..., min_length=1, description="File path to the policy PDF.")
    policy_id: str | None = Field(default=None, description="Optional policy ID override.")
    user_id: str | None = Field(default=None, description="Optional tenant/user identifier for isolation.")
    force_reindex: bool = Field(default=False, description="If True, bypasses duplicate index check.")


class PolicyIndexResponse(BaseModel):
    """Response contract for policy indexing."""

    model_config = ConfigDict(frozen=True)

    status: str = Field(default="indexed", description="Indexing status.")
    policy_id: str = Field(..., description="Target policy identifier.")
    user_id: str | None = Field(default=None, description="Associated user/tenant ID.")
    indexed_chunks: int = Field(..., ge=0, description="Total clause chunks stored.")
    content_hash: str = Field(..., description="SHA-256 checksum of the indexed PDF.")
    is_duplicate: bool = Field(default=False, description="True if indexing was skipped due to duplicate hash.")
    execution_time_ms: float = Field(..., ge=0.0, description="Indexing duration in milliseconds.")
    warnings: list[str] = Field(default_factory=list, description="Notices or warnings during indexing.")


class ClauseRetrieveRequest(BaseModel):
    """Request contract for retrieving relevant policy clauses."""

    model_config = ConfigDict(frozen=True)

    policy_id: str = Field(..., min_length=1, description="Target policy identifier.")
    query: str = Field(..., min_length=1, description="Search query or procedure phrase.")
    user_id: str | None = Field(default=None, description="Optional user/tenant ID for scoping.")
    top_k: int = Field(default=5, ge=1, le=20, description="Maximum number of clauses to retrieve.")


class RetrievedClauseItem(BaseModel):
    """A single retrieved clause matched against a query."""

    model_config = ConfigDict(frozen=True)

    chunk_id: str = Field(..., description="Deterministic chunk ID.")
    page_number: int = Field(..., ge=1, description="1-indexed PDF page number.")
    section_title: str | None = Field(default=None, description="Section heading.")
    similarity_score: float = Field(..., ge=0.0, le=1.0, description="Hybrid similarity score.")
    text: str = Field(..., description="Verbatim chunk text snippet.")


class ClauseRetrieveResponse(BaseModel):
    """Response contract for clause retrieval."""

    model_config = ConfigDict(frozen=True)

    policy_id: str = Field(..., description="Target policy identifier.")
    user_id: str | None = Field(default=None, description="Scoping tenant/user ID.")
    query: str = Field(..., description="Executed search query.")
    matches_count: int = Field(..., ge=0, description="Number of matching clauses returned.")
    clauses: list[RetrievedClauseItem] = Field(default_factory=list, description="List of matched clauses.")
    execution_time_ms: float = Field(..., ge=0.0, description="Retrieval latency in milliseconds.")


class PolicyQuestionRequest(BaseModel):
    """Request contract for asking an insurance policy question."""

    model_config = ConfigDict(frozen=True)

    policy_id: str = Field(..., min_length=1, description="Target policy identifier.")
    question: str = Field(..., min_length=2, description="Inquiry regarding coverage, costs, or exclusions.")
    user_id: str | None = Field(default=None, description="Optional user/tenant ID for scoping.")
    conversation_history: list[dict[str, Any]] | None = Field(default=None, description="Optional previous messages for context.")


class PolicyQuestionResponse(BaseModel):
    """Response contract for grounded policy Q&A."""

    model_config = ConfigDict(frozen=True)

    policy_id: str = Field(..., description="Target policy identifier.")
    user_id: str | None = Field(default=None, description="Scoping tenant/user ID.")
    question: str = Field(..., description="Original user inquiry.")
    answer: str = Field(..., description="Audit-grounded answer or explicit refusal.")
    grounded: bool = Field(..., description="True if answer is backed by retrieved policy clauses.")
    confidence: str = Field(default="High", description="Structured confidence level (High, Medium, Low, Insufficient evidence).")
    citations: list[Citation] = Field(default_factory=list, description="Exact 1-indexed page citations.")
    retrieved_clauses_count: int = Field(default=0, ge=0, description="Number of clauses evaluated.")
    is_live_model: bool = Field(..., description="True if live Ollama LLM generated the output.")
    model_name: str = Field(..., description="Active generation model name or synthesizer tag.")
    fallback_used: bool = Field(..., description="True if deterministic fallback was triggered.")
    warnings: list[str] = Field(default_factory=list, description="Prior authorization and limitation warnings.")
    execution_time_ms: float = Field(..., ge=0.0, description="Inference latency in milliseconds.")


class AIHealthCheckResponse(BaseModel):
    """Response contract for AI/ML module health and runtime readiness."""

    model_config = ConfigDict(frozen=True)

    status: str = Field(default="healthy", description="Overall health ('healthy', 'degraded', 'unhealthy').")
    ollama_online: bool = Field(..., description="True if local Ollama server is reachable.")
    llm_model: str = Field(..., description="Configured LLM model name.")
    llm_model_available: bool = Field(..., description="True if target LLM model is pulled.")
    embedding_model: str = Field(..., description="Embedding model name.")
    embedding_dimension: int = Field(default=1024, description="Embedding vector dimensionality.")
    embedding_loaded: bool = Field(..., description="True if embedding model weights are loaded in memory.")
    database_type: str = Field(..., description="Active vector store type ('postgres' or 'in_memory').")
    database_connected: bool = Field(..., description="True if database connection check succeeded.")
    diagnostic_details: str = Field(default="", description="Diagnostic message or fallback notice.")


class PolicyDeleteRequest(BaseModel):
    """Request contract for deleting an indexed policy from the vector store."""

    model_config = ConfigDict(frozen=True)

    policy_id: str = Field(..., min_length=1, description="Target policy identifier.")
    user_id: str | None = Field(default=None, description="Optional user/tenant ID for scoping.")


class PolicyDeleteResponse(BaseModel):
    """Response contract for policy deletion."""

    model_config = ConfigDict(frozen=True)

    status: str = Field(default="deleted", description="Deletion status ('deleted' or 'not_found').")
    policy_id: str = Field(..., description="Target policy identifier.")
    user_id: str | None = Field(default=None, description="Associated user/tenant ID.")
    deleted_chunks: int = Field(..., ge=0, description="Total chunks purged from the vector index.")
    execution_time_ms: float = Field(..., ge=0.0, description="Execution duration in milliseconds.")
