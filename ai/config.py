"""Configuration management for CoverWise AI AI/ML module.

Uses Pydantic Settings v2 to load, validate, and manage environment variables.
"""

from functools import lru_cache
import logging
from pathlib import Path
import sys
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Base directory for the AI module and repository
AI_DIR = Path(__file__).resolve().parent
REPO_ROOT = AI_DIR.parent


class Settings(BaseSettings):
    """Application settings for AI/ML module with strict validation."""

    model_config = SettingsConfigDict(
        env_file=(
            str(AI_DIR / ".env"),
            str(REPO_ROOT / ".env"),
        ),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # LLM Settings (Ollama / Qwen)
    ollama_base_url: str = Field(
        default="http://localhost:11434",
        description="Base URL for the local or remote Ollama server instance.",
    )
    llm_model: str = Field(
        default="qwen2.5:7b",
        description="Target LLM model tag in Ollama (e.g., qwen2.5:7b, qwen2.5:14b).",
    )
    llm_temperature: float = Field(
        default=0.0,
        ge=0.0,
        le=2.0,
        description="Sampling temperature for deterministic extraction.",
    )
    llm_timeout_seconds: int = Field(
        default=60,
        ge=5,
        description="HTTP timeout in seconds for LLM generation requests.",
    )

    # Retrieval & Embeddings Settings (BGE-M3 default)
    embedding_model: str = Field(
        default="BAAI/bge-m3",
        description="HuggingFace model ID for generating dense/sparse policy embeddings.",
    )
    database_url: str | None = Field(
        default=None,
        description="PostgreSQL connection string with pgvector extension enabled.",
    )
    vector_table_name: str = Field(
        default="policy_embeddings",
        description="Table name storing policy vector chunks and metadata.",
    )
    vector_dimension: int = Field(
        default=1024,
        ge=128,
        description="Dimension of the embedding vectors (1024 for BGE-M3).",
    )

    # Chunking Parameters
    chunk_size: int = Field(
        default=500,
        gt=0,
        description="Target chunk size in tokens/characters for retrieval.",
    )
    chunk_overlap: int = Field(
        default=100,
        ge=0,
        description="Overlap between consecutive chunks to maintain context.",
    )

    # Optical Character Recognition (OCR)
    enable_ocr: bool = Field(
        default=False,
        description="Flag to enable OCR fallback for scanned or non-text PDFs.",
    )
    ocr_engine: Literal["paddleocr", "tesseract"] = Field(
        default="paddleocr",
        description="Target OCR engine when OCR fallback is enabled.",
    )

    # Runtime Environment
    environment: Literal["development", "testing", "production"] = Field(
        default="development",
        description="Runtime execution environment.",
    )
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO",
        description="Global logging level.",
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached instance of the settings."""
    return Settings()


def setup_logging(level: str | None = None) -> logging.Logger:
    """Configure structured logging for the AI module.

    Args:
        level: Optional log level override (DEBUG, INFO, etc.).

    Returns:
        Configured root logger for the ai module.
    """
    effective_level = level or get_settings().log_level
    numeric_level = getattr(logging, effective_level.upper(), logging.INFO)

    logger = logging.getLogger("coverwise_ai")
    logger.setLevel(numeric_level)

    # Avoid duplicate handlers if setup_logging is invoked multiple times
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(numeric_level)
        formatter = logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] [%(name)s:%(funcName)s:%(lineno)d] - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger
