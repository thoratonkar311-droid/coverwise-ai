"""Central integration service for CoverWise AI AI/ML module.

Coordinates:
- Policy extraction with Pydantic validation
- Vector indexing with duplicate prevention
- Hybrid clause retrieval with tenant isolation
- Grounded Q&A with live-vs-fallback reporting
- Health checks and database connectivity diagnostics
"""

import hashlib
import logging
from pathlib import Path
import time
from typing import Any

from ai.config import get_settings
from ai.extraction.policy_extractor import extract_policy
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
    PolicyDeleteRequest,
    PolicyDeleteResponse,
    RetrievedClauseItem,
)
from ai.integration.security import (
    install_sensitive_log_filter,
    mask_sensitive_phi,
    validate_pdf_file,
)
from ai.llm.client import OllamaClient
from ai.retrieval.embeddings import get_embedding_model
from ai.retrieval.retriever import (
    answer_policy_question,
    get_default_vector_store,
    index_policy,
    retrieve_clauses,
)
from ai.retrieval.vector_store import (
    VectorStoreInterface,
    check_database_connectivity,
)

logger = logging.getLogger("coverwise_ai.integration.service")

# Initialize sensitive log filter
install_sensitive_log_filter()


class AIService:
    """Production-grade AI integration service for CoverWise AI."""

    def __init__(
        self,
        vector_store: VectorStoreInterface | None = None,
        llm_client: OllamaClient | None = None,
    ) -> None:
        """Initialize AIService with optional vector store and LLM client overrides."""
        self.settings = get_settings()
        self.vector_store = vector_store or get_default_vector_store()
        self.llm_client = llm_client or OllamaClient(
            model=self.settings.llm_model,
            timeout_seconds=self.settings.llm_timeout_seconds,
        )

    def extract_policy(self, request: PolicyExtractRequest) -> PolicyExtractResponse:
        """Extract structured insurance policy intelligence preserving exact page citations."""
        t_start = time.perf_counter()

        # Security check: validate PDF upload
        safe_path = validate_pdf_file(request.pdf_path)

        logger.info(
            "Extracting policy from '%s' (user_id=%s)",
            safe_path.name,
            request.user_id,
        )
        policy = extract_policy(str(safe_path))

        warnings: list[str] = []
        if policy.conflicting_evidence:
            warnings.append(f"{len(policy.conflicting_evidence)} conflicting evidence items detected across policy clauses.")
        for pa in policy.prior_authorizations:
            warnings.append(f"Prior authorization requirement: {pa.service_or_procedure} [{pa.timeline_requirement}].")

        t_elapsed = (time.perf_counter() - t_start) * 1000.0

        return PolicyExtractResponse(
            status="success",
            policy=policy,
            execution_time_ms=round(t_elapsed, 2),
            warnings=warnings,
        )

    def index_policy(self, request: PolicyIndexRequest) -> PolicyIndexResponse:
        """Index a policy PDF into the vector store with duplicate indexing prevention."""
        t_start = time.perf_counter()

        # Security check: validate PDF upload
        safe_path = validate_pdf_file(request.pdf_path)
        content_hash = hashlib.sha256(safe_path.read_bytes()).hexdigest()

        assigned_id = request.policy_id or safe_path.stem
        user_id = request.user_id

        # Check for duplicate indexing
        is_dup = False
        warnings: list[str] = []

        if not request.force_reindex:
            existing = self.vector_store.get_chunks_by_document(assigned_id, user_id=user_id)
            if existing and all(c.metadata.get("content_hash") == content_hash for c in existing):
                is_dup = True
                warnings.append(f"Policy '{assigned_id}' with matching checksum already indexed. Duplicate re-indexing skipped.")
                t_elapsed = (time.perf_counter() - t_start) * 1000.0
                return PolicyIndexResponse(
                    status="already_indexed",
                    policy_id=assigned_id,
                    user_id=user_id,
                    indexed_chunks=len(existing),
                    content_hash=content_hash,
                    is_duplicate=True,
                    execution_time_ms=round(t_elapsed, 2),
                    warnings=warnings,
                )

        count = index_policy(
            pdf_path=safe_path,
            policy_id=assigned_id,
            user_id=user_id,
            vector_store=self.vector_store,
            force_reindex=request.force_reindex,
        )

        t_elapsed = (time.perf_counter() - t_start) * 1000.0
        return PolicyIndexResponse(
            status="indexed",
            policy_id=assigned_id,
            user_id=user_id,
            indexed_chunks=count,
            content_hash=content_hash,
            is_duplicate=is_dup,
            execution_time_ms=round(t_elapsed, 2),
            warnings=warnings,
        )

    def delete_policy(self, request: PolicyDeleteRequest) -> PolicyDeleteResponse:
        """Purge an indexed policy and its chunks from the vector store."""
        t_start = time.perf_counter()
        logger.info("Purging policy '%s' from vector store (user_id=%s)", request.policy_id, request.user_id)

        deleted_count = self.vector_store.delete_by_document(
            document_id=request.policy_id,
            user_id=request.user_id,
        )

        status = "deleted" if deleted_count > 0 else "not_found"
        t_elapsed = (time.perf_counter() - t_start) * 1000.0

        return PolicyDeleteResponse(
            status=status,
            policy_id=request.policy_id,
            user_id=request.user_id,
            deleted_chunks=deleted_count,
            execution_time_ms=round(t_elapsed, 2),
        )

    def retrieve_clauses(self, request: ClauseRetrieveRequest) -> ClauseRetrieveResponse:
        """Retrieve relevant clauses using hybrid search with cross-user isolation."""
        t_start = time.perf_counter()

        # Sanitize query for logging to prevent PHI exposure
        clean_query = mask_sensitive_phi(request.query)
        logger.debug("Retrieving clauses for policy '%s' (user_id=%s): '%s'", request.policy_id, request.user_id, clean_query)

        raw_results = retrieve_clauses(
            policy_id=request.policy_id,
            query=request.query,
            top_k=request.top_k,
            user_id=request.user_id,
            vector_store=self.vector_store,
        )

        clauses: list[RetrievedClauseItem] = [
            RetrievedClauseItem(
                chunk_id=r.chunk.chunk_id,
                page_number=r.chunk.page_number,
                section_title=r.chunk.section_title,
                similarity_score=round(r.similarity_score, 4),
                text=r.chunk.text,
            )
            for r in raw_results
        ]

        t_elapsed = (time.perf_counter() - t_start) * 1000.0
        return ClauseRetrieveResponse(
            policy_id=request.policy_id,
            user_id=request.user_id,
            query=request.query,
            matches_count=len(clauses),
            clauses=clauses,
            execution_time_ms=round(t_elapsed, 2),
        )

    def answer_question(self, request: PolicyQuestionRequest) -> PolicyQuestionResponse:
        """Answer an insurance question strictly grounded in policy evidence."""
        t_start = time.perf_counter()

        # Sanitize question for logging
        clean_q = mask_sensitive_phi(request.question)
        logger.info("Answering question for policy '%s' (user_id=%s): '%s'", request.policy_id, request.user_id, clean_q)

        raw_res = answer_policy_question(
            policy_id=request.policy_id,
            question=request.question,
            user_id=request.user_id,
            vector_store=self.vector_store,
            llm_client=self.llm_client,
            conversation_history=request.conversation_history,
        )

        t_elapsed = (time.perf_counter() - t_start) * 1000.0
        return PolicyQuestionResponse(
            policy_id=raw_res["policy_id"],
            user_id=raw_res.get("user_id"),
            question=raw_res["question"],
            answer=raw_res["answer"],
            grounded=raw_res["grounded"],
            confidence=raw_res.get("confidence", "High" if raw_res.get("grounded") else "Insufficient evidence"),
            citations=raw_res.get("citations", []),
            retrieved_clauses_count=raw_res.get("retrieved_clauses_count", 0),
            is_live_model=raw_res.get("is_live_model", False),
            model_name=raw_res.get("model_name", "unknown"),
            fallback_used=raw_res.get("fallback_used", False),
            warnings=raw_res.get("warnings", []),
            execution_time_ms=round(t_elapsed, 2),
        )

    def check_health(self) -> AIHealthCheckResponse:
        """Evaluate overall AI/ML system readiness and health."""
        ollama_up = self.llm_client.check_health()
        model_available = False
        if ollama_up:
            try:
                models = self.llm_client.list_models()
                model_available = any(
                    self.settings.llm_model in m or m.startswith(self.settings.llm_model.split(":")[0])
                    for m in models
                )
            except Exception:
                model_available = False

        embedder = get_embedding_model()
        emb_loaded = getattr(embedder, "_is_loaded", False)

        db_connected, db_diag = check_database_connectivity(self.settings.database_url)
        db_type = "postgres" if (self.settings.database_url and db_connected) else "in_memory"

        status = "healthy"
        if not ollama_up or not model_available:
            status = "degraded"

        return AIHealthCheckResponse(
            status=status,
            ollama_online=ollama_up,
            llm_model=self.settings.llm_model,
            llm_model_available=model_available,
            embedding_model=self.settings.embedding_model,
            embedding_dimension=self.settings.vector_dimension,
            embedding_loaded=emb_loaded,
            database_type=db_type,
            database_connected=db_connected,
            diagnostic_details=db_diag,
        )


# Global singleton instance
_GLOBAL_AI_SERVICE: AIService | None = None


def get_ai_service() -> AIService:
    """Return the global AIService singleton instance."""
    global _GLOBAL_AI_SERVICE
    if _GLOBAL_AI_SERVICE is None:
        _GLOBAL_AI_SERVICE = AIService()
    return _GLOBAL_AI_SERVICE
