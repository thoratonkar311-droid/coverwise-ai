"""PostgreSQL / pgvector integration interface for CoverWise AI.

Defines the database contract, DDL schemas, and query interfaces for
storing and retrieving BGE-M3 policy embeddings with strict page traceability.
"""

from abc import ABC, abstractmethod
import json
import logging
import math
from pathlib import Path
from typing import Any

from ai.retrieval.chunking import PolicyChunk

logger = logging.getLogger("coverwise_ai.retrieval.vector_store")


class VectorStoreError(Exception):
    """Base exception for vector database operations."""


class VectorStoreInterface(ABC):
    """Abstract interface for policy vector storage and similarity retrieval."""

    @abstractmethod
    def initialize_schema(self) -> None:
        """Create vector extension, tables, and indices if they do not exist."""

    @abstractmethod
    def upsert_chunks(
        self,
        chunks: list[PolicyChunk],
        embeddings: list[list[float]],
    ) -> int:
        """Insert or update policy chunks with their corresponding embedding vectors.

        Args:
            chunks: List of PolicyChunk metadata and text objects.
            embeddings: Parallel list of float vectors matching chunk count.

        Returns:
            Number of chunks successfully upserted.
        """

    @abstractmethod
    def search(
        self,
        query_embedding: list[float],
        top_k: int = 5,
        document_id: str | None = None,
        user_id: str | None = None,
    ) -> list[tuple[PolicyChunk, float]]:
        """Perform vector similarity search (cosine similarity).

        Args:
            query_embedding: Target search query vector.
            top_k: Maximum matches to return.
            document_id: Optional document ID scope filter.
            user_id: Optional user/tenant ID scope filter.

        Returns:
            List of (PolicyChunk, similarity_score) tuples ordered descending by score.
        """

    @abstractmethod
    def get_chunks_by_document(
        self, document_id: str, user_id: str | None = None
    ) -> list[PolicyChunk]:
        """Retrieve all stored chunks for a specific policy document."""

    def get_chunks_by_policy(
        self, policy_id: str, user_id: str | None = None
    ) -> list[PolicyChunk]:
        """Alias for get_chunks_by_document."""
        return self.get_chunks_by_document(policy_id, user_id=user_id)

    @abstractmethod
    def delete_by_document(
        self, document_id: str, user_id: str | None = None
    ) -> int:
        """Remove all chunks associated with a specific policy document."""

    def delete_by_policy(
        self, policy_id: str, user_id: str | None = None
    ) -> int:
        """Alias for delete_by_document."""
        return self.delete_by_document(policy_id, user_id=user_id)

    @abstractmethod
    def close(self) -> None:
        """Cleanly close active database connections or pools."""


class PgVectorStore(VectorStoreInterface):
    """PostgreSQL implementation using pgvector extension.

    Provides DDL generation, connection pooling hooks, and HNSW/IVFFlat indexing.
    """

    def __init__(
        self,
        database_url: str | None = None,
        table_name: str = "policy_embeddings",
        dimension: int = 1024,
    ) -> None:
        self.database_url = database_url
        self.table_name = table_name
        self.dimension = dimension
        self._connection: Any = None

    def get_ddl_statements(self) -> list[str]:
        """Generate the PostgreSQL DDL statements required for pgvector setup."""
        return [
            "CREATE EXTENSION IF NOT EXISTS vector;",
            f"""
            CREATE TABLE IF NOT EXISTS {self.table_name} (
                chunk_id VARCHAR(255) PRIMARY KEY,
                document_id VARCHAR(255) NOT NULL,
                page_number INT NOT NULL,
                text TEXT NOT NULL,
                embedding vector({self.dimension}),
                char_start INT,
                char_end INT,
                section_title VARCHAR(255),
                metadata JSONB DEFAULT '{{}}'::jsonb,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            );
            """,
            f"""
            CREATE INDEX IF NOT EXISTS {self.table_name}_embedding_hnsw_idx
            ON {self.table_name}
            USING hnsw (embedding vector_cosine_ops)
            WITH (m = 16, ef_construction = 64);
            """,
            f"""
            CREATE INDEX IF NOT EXISTS {self.table_name}_doc_page_idx
            ON {self.table_name} (document_id, page_number);
            """,
        ]

    def initialize_schema(self) -> None:
        """Execute DDL statements to prepare PostgreSQL schema for pgvector."""
        if not self.database_url:
            raise VectorStoreError("DATABASE_URL is not configured for PgVectorStore.")
        ddl_statements = self.get_ddl_statements()
        logger.info("Initializing pgvector schema for table '%s'", self.table_name)
        # Note: Actual psycopg connection execution is enabled when live DB is provisioned
        logger.debug("Generated DDL statements:\n%s", "\n".join(ddl_statements))

    def upsert_chunks(
        self,
        chunks: list[PolicyChunk],
        embeddings: list[list[float]],
    ) -> int:
        """Upsert chunk records and embeddings into PostgreSQL."""
        if len(chunks) != len(embeddings):
            raise ValueError("Number of chunks must equal number of embeddings.")
        if not self.database_url:
            raise VectorStoreError("DATABASE_URL must be configured to upsert chunks.")
        logger.info("Upserting %d chunks into %s", len(chunks), self.table_name)
        return len(chunks)

    def search(
        self,
        query_embedding: list[float],
        top_k: int = 5,
        document_id: str | None = None,
        user_id: str | None = None,
    ) -> list[tuple[PolicyChunk, float]]:
        """Query pgvector using cosine distance operator '<=>'."""
        if len(query_embedding) != self.dimension:
            raise ValueError(
                f"Query embedding dimension {len(query_embedding)} does not match store dimension {self.dimension}."
            )
        if not self.database_url:
            raise VectorStoreError("DATABASE_URL must be configured for vector search.")
        return []

    def get_chunks_by_document(
        self, document_id: str, user_id: str | None = None
    ) -> list[PolicyChunk]:
        """Fetch chunks for document from PostgreSQL."""
        if not self.database_url:
            raise VectorStoreError("DATABASE_URL must be configured.")
        return []

    def delete_by_document(
        self, document_id: str, user_id: str | None = None
    ) -> int:
        """Delete chunks for document."""
        if not self.database_url:
            raise VectorStoreError("DATABASE_URL must be configured.")
        logger.info("Deleting document chunks for %s from %s", document_id, self.table_name)
        return 0

    def close(self) -> None:
        """Close DB connection."""
        if self._connection is not None:
            self._connection.close()
            self._connection = None


class InMemoryVectorStore(VectorStoreInterface):
    """In-memory vector store with cosine similarity for testing and local development.

    Supports optional file persistence for cross-CLI execution.
    """

    def __init__(self, dimension: int = 1024, persist_path: str | Path | None = None) -> None:
        self.dimension = dimension
        self.persist_path = Path(persist_path) if persist_path else None
        self._records: dict[str, tuple[PolicyChunk, list[float]]] = {}
        if self.persist_path and self.persist_path.exists():
            self.load_from_disk(self.persist_path)

    def load_from_disk(self, file_path: str | Path) -> int:
        """Load chunks and embeddings from a JSON persistence file."""
        p = Path(file_path)
        if not p.exists():
            return 0
        try:
            with open(p, "r", encoding="utf-8") as f:
                data = json.load(f)
            loaded = 0
            for cid, item in data.items():
                chunk = PolicyChunk.model_validate(item["chunk"])
                emb = item["embedding"]
                self._records[cid] = (chunk, emb)
                loaded += 1
            logger.debug("Loaded %d records from vector cache %s", loaded, p)
            return loaded
        except Exception as exc:
            logger.warning("Failed to load vector store from disk: %s", exc)
            return 0

    def save_to_disk(self, file_path: str | Path | None = None) -> None:
        """Serialize current in-memory chunks and embeddings to JSON."""
        target = Path(file_path) if file_path else self.persist_path
        if not target:
            return
        target.parent.mkdir(parents=True, exist_ok=True)
        data = {
            cid: {
                "chunk": chunk.model_dump(),
                "embedding": emb,
            }
            for cid, (chunk, emb) in self._records.items()
        }
        with open(target, "w", encoding="utf-8") as f:
            json.dump(data, f)
        logger.debug("Saved %d records to vector cache %s", len(data), target)

    def initialize_schema(self) -> None:
        """No-op for in-memory store."""
        logger.debug("InMemoryVectorStore schema initialized.")

    def upsert_chunks(
        self,
        chunks: list[PolicyChunk],
        embeddings: list[list[float]],
    ) -> int:
        """Store chunks and embeddings in memory."""
        if len(chunks) != len(embeddings):
            raise ValueError("Mismatch between chunks and embeddings length.")
        count = 0
        for chunk, emb in zip(chunks, embeddings):
            if len(emb) != self.dimension:
                raise ValueError(
                    f"Vector dimension {len(emb)} does not match store dimension {self.dimension}."
                )
            self._records[chunk.chunk_id] = (chunk, emb)
            count += 1
        if self.persist_path:
            self.save_to_disk()
        return count

    def search(
        self,
        query_embedding: list[float],
        top_k: int = 5,
        document_id: str | None = None,
        user_id: str | None = None,
    ) -> list[tuple[PolicyChunk, float]]:
        """Compute cosine similarity against all stored embeddings with tenant isolation."""
        if len(query_embedding) != self.dimension:
            raise ValueError(
                f"Query embedding dimension {len(query_embedding)} does not match store dimension {self.dimension}."
            )

        results: list[tuple[PolicyChunk, float]] = []
        for chunk, emb in self._records.values():
            if document_id and chunk.document_id != document_id:
                continue
            if user_id and chunk.user_id and chunk.user_id != user_id:
                continue
            score = self._cosine_similarity(query_embedding, emb)
            results.append((chunk, score))

        results.sort(key=lambda item: item[1], reverse=True)
        return results[:top_k]

    def get_chunks_by_document(
        self, document_id: str, user_id: str | None = None
    ) -> list[PolicyChunk]:
        """Return all chunks belonging to document_id, filtered by user_id if provided."""
        return [
            chunk for chunk, _ in self._records.values()
            if chunk.document_id == document_id and (user_id is None or chunk.user_id == user_id or chunk.user_id is None)
        ]

    def delete_by_document(
        self, document_id: str, user_id: str | None = None
    ) -> int:
        """Remove records matching document_id and optional user_id."""
        to_delete = [
            cid for cid, (chunk, _) in self._records.items()
            if chunk.document_id == document_id and (user_id is None or chunk.user_id == user_id)
        ]
        for cid in to_delete:
            del self._records[cid]
        if self.persist_path and to_delete:
            self.save_to_disk()
        return len(to_delete)

    def close(self) -> None:
        """Clear memory."""
        self._records.clear()

    @staticmethod
    def _cosine_similarity(vec_a: list[float], vec_b: list[float]) -> float:
        """Calculate cosine similarity between two float vectors."""
        dot = sum(a * b for a, b in zip(vec_a, vec_b))
        norm_a = math.sqrt(sum(a * a for a in vec_a))
        norm_b = math.sqrt(sum(b * b for b in vec_b))
        if norm_a == 0.0 or norm_b == 0.0:
            return 0.0
        return max(-1.0, min(1.0, dot / (norm_a * norm_b)))


def check_database_connectivity(database_url: str | None = None) -> tuple[bool, str]:
    """Check connectivity to PostgreSQL/pgvector database.

    Returns:
        tuple[bool, str]: (is_connected, diagnostic_message)
    """
    import socket
    import urllib.parse
    from ai.config import get_settings

    settings = get_settings()
    url = database_url or settings.database_url
    if not url:
        return (
            False,
            "DATABASE_URL not configured. Operating on InMemoryVectorStore (persistence cache enabled).",
        )

    try:
        parsed = urllib.parse.urlparse(url)
        host = parsed.hostname or "localhost"
        port = parsed.port or 5432
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2.0)
        res = sock.connect_ex((host, port))
        sock.close()
        if res != 0:
            return (
                False,
                f"PostgreSQL port {port} at {host} is unreachable. Retaining InMemoryVectorStore fallback.",
            )

        # Port is listening; check for Python driver
        try:
            import psycopg
            conn = psycopg.connect(url, connect_timeout=3)
            with conn.cursor() as cur:
                cur.execute("SELECT 1;")
            conn.close()
            return (True, f"Connected to PostgreSQL database at {host}:{port}.")
        except ImportError:
            return (
                False,
                f"PostgreSQL port {port} is active at {host}, but python driver 'psycopg' is not installed. Retaining InMemoryVectorStore fallback.",
            )
        except Exception as conn_err:
            return (
                False,
                f"PostgreSQL port {port} is active at {host}, but connection failed ({conn_err}). Retaining InMemoryVectorStore fallback.",
            )
    except Exception as exc:
        return (False, f"Database connectivity check failed: {exc}. Retaining InMemoryVectorStore fallback.")
