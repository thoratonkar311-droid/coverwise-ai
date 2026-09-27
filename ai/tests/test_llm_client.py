"""Tests for Ollama client configuration, error handling, and connectivity."""

import pytest
from unittest import mock
import httpx

from ai.llm.client import (
    OllamaClient,
    OllamaConnectionError,
    OllamaResponseError,
)


def test_ollama_client_defaults():
    """Verify default client parameters inherit from Settings."""
    client = OllamaClient()
    assert client.base_url == "http://localhost:11434"
    assert "qwen" in client.model.lower()
    assert client.timeout_seconds > 0


def test_ollama_health_check_handles_unreachable_server():
    """Verify health check returns False gracefully when server is offline."""
    # Point to guaranteed non-existent local port
    client = OllamaClient(base_url="http://127.0.0.1:59999", timeout_seconds=1)
    assert client.check_health() is False


def test_ollama_generate_connection_error_handling():
    """Verify OllamaConnectionError is raised when connection fails."""
    client = OllamaClient(base_url="http://127.0.0.1:59999", timeout_seconds=1)
    with pytest.raises(OllamaConnectionError):
        client.generate(prompt="Hello")


def test_ollama_generate_success_mock():
    """Verify successful generation parse with mocked response."""
    client = OllamaClient()
    mock_response = httpx.Response(
        status_code=200,
        json={"response": "Deductible is $1500"},
        request=httpx.Request("POST", f"{client.base_url}/api/generate"),
    )

    with mock.patch("httpx.Client.post", return_value=mock_response):
        res = client.generate("What is deductible?")
        assert res == "Deductible is $1500"
