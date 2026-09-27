"""LLM integration module for CoverWise AI.

Exposes Ollama client and custom exception classes.
"""

from ai.llm.client import (
    OllamaClient,
    OllamaClientError,
    OllamaConnectionError,
    OllamaModelNotFoundError,
    OllamaResponseError,
)

__all__ = [
    "OllamaClient",
    "OllamaClientError",
    "OllamaConnectionError",
    "OllamaModelNotFoundError",
    "OllamaResponseError",
]
