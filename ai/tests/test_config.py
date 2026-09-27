"""Tests for AI module configuration and environment variable loading."""

import os
from unittest import mock
import pytest
from ai.config import Settings, get_settings, setup_logging


def test_default_settings():
    """Verify default settings adhere to project architecture specs."""
    settings = Settings()
    assert settings.ollama_base_url == "http://localhost:11434"
    assert "qwen" in settings.llm_model.lower()
    assert settings.embedding_model == "BAAI/bge-m3"
    assert settings.vector_dimension == 1024
    assert settings.enable_ocr is False
    assert settings.environment in ("development", "testing")


def test_settings_env_override():
    """Verify settings pick up environment variable overrides correctly."""
    with mock.patch.dict(
        os.environ,
        {
            "OLLAMA_BASE_URL": "http://gpu-cluster:11434",
            "LLM_MODEL": "qwen2.5:14b",
            "EMBEDDING_MODEL": "BAAI/bge-m3",
            "VECTOR_DIMENSION": "1024",
            "ENABLE_OCR": "true",
            "LOG_LEVEL": "DEBUG",
        },
    ):
        settings = Settings()
        assert settings.ollama_base_url == "http://gpu-cluster:11434"
        assert settings.llm_model == "qwen2.5:14b"
        assert settings.enable_ocr is True
        assert settings.log_level == "DEBUG"


def test_get_settings_caching():
    """Verify get_settings returns consistent cached instance."""
    s1 = get_settings()
    s2 = get_settings()
    assert s1 is s2


def test_setup_logging():
    """Verify logging setup initializes logger with proper level."""
    logger = setup_logging(level="DEBUG")
    assert logger.name == "coverwise_ai"
    assert logger.level == 10  # DEBUG
