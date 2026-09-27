"""Ollama LLM client integration for CoverWise AI.

Provides a robust HTTP client wrapper for local or remote Ollama instances,
targeting Qwen models (e.g. qwen2.5:7b) for structured policy extraction.
"""

import logging
from typing import Any
import httpx

from ai.config import get_settings

logger = logging.getLogger("coverwise_ai.llm.client")


class OllamaClientError(Exception):
    """Base exception for Ollama interactions."""


class OllamaConnectionError(OllamaClientError):
    """Raised when the Ollama server cannot be reached."""


class OllamaModelNotFoundError(OllamaClientError):
    """Raised when the specified model tag is not pulled or available in Ollama."""


class OllamaResponseError(OllamaClientError):
    """Raised when Ollama returns an error payload or bad HTTP status."""


class OllamaClient:
    """Configurable client for communicating with Ollama API endpoints."""

    def __init__(
        self,
        base_url: str | None = None,
        model: str | None = None,
        timeout_seconds: int | None = None,
        default_temperature: float | None = None,
    ) -> None:
        settings = get_settings()
        self.base_url = (base_url or settings.ollama_base_url).rstrip("/")
        self.model = model or settings.llm_model
        self.timeout_seconds = timeout_seconds or settings.llm_timeout_seconds
        self.default_temperature = (
            default_temperature if default_temperature is not None else settings.llm_temperature
        )

    def check_health(self) -> bool:
        """Check if the Ollama server is accessible."""
        url = f"{self.base_url}/api/version"
        try:
            with httpx.Client(timeout=5.0) as client:
                resp = client.get(url)
                return resp.status_code == 200
        except Exception as exc:
            logger.debug("Ollama health check failed at %s: %s", url, exc)
            return False

    def list_models(self) -> list[str]:
        """Fetch list of pulled model names currently available in Ollama."""
        url = f"{self.base_url}/api/tags"
        try:
            with httpx.Client(timeout=5.0) as client:
                resp = client.get(url)
                if resp.status_code != 200:
                    raise OllamaResponseError(
                        f"Failed to fetch tags: HTTP {resp.status_code} - {resp.text}"
                    )
                data = resp.json()
                models = [item.get("name", "") for item in data.get("models", [])]
                return [m for m in models if m]
        except httpx.RequestError as exc:
            raise OllamaConnectionError(f"Could not connect to Ollama at {self.base_url}: {exc}") from exc

    def is_model_available(self, model_name: str | None = None) -> bool:
        """Verify whether a target model tag exists locally in Ollama."""
        target = model_name or self.model
        try:
            available = self.list_models()
            return any(target in m or m.startswith(target.split(":")[0]) for m in available)
        except OllamaConnectionError:
            return False

    def generate(
        self,
        prompt: str,
        system: str | None = None,
        temperature: float | None = None,
        format_json: bool = False,
        options: dict[str, Any] | None = None,
    ) -> str:
        """Send a single prompt completion request to Ollama.

        Args:
            prompt: User prompt content.
            system: Optional system instruction prompt.
            temperature: Sampling temperature override.
            format_json: If True, instructs Ollama to enforce valid JSON output format.
            options: Optional dict of Ollama runtime parameters (e.g. num_predict).

        Returns:
            Generated response string.
        """
        url = f"{self.base_url}/api/generate"
        gen_opts: dict[str, Any] = {
            "temperature": (
                temperature if temperature is not None else self.default_temperature
            ),
        }
        if options:
            gen_opts.update(options)

        payload: dict[str, Any] = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": gen_opts,
        }
        if system:
            payload["system"] = system
        if format_json:
            payload["format"] = "json"

        logger.debug("Dispatching generation to Ollama model '%s' at %s", self.model, url)

        try:
            with httpx.Client(timeout=float(self.timeout_seconds)) as client:
                resp = client.post(url, json=payload)
                if resp.status_code != 200:
                    raise OllamaResponseError(
                        f"Ollama generation failed (HTTP {resp.status_code}): {resp.text}"
                    )
                data = resp.json()
                text = data.get("response", "")
                if not text and "thinking" in data:
                    text = data.get("thinking", "")
                if "</think>" in text:
                    tail = text.split("</think>")[-1].strip()
                    if tail:
                        text = tail
                return text
        except httpx.RequestError as exc:
            logger.error("Ollama connection failed: %s", exc)
            raise OllamaConnectionError(
                f"Failed to connect to Ollama server at {self.base_url}. Ensure Ollama is running."
            ) from exc

    def chat(
        self,
        messages: list[dict[str, str]],
        temperature: float | None = None,
        format_json: bool = False,
        options: dict[str, Any] | None = None,
    ) -> str:
        """Send a multi-turn chat completion request to Ollama.

        Args:
            messages: List of message dicts with 'role' and 'content' keys.
            temperature: Sampling temperature override.
            format_json: If True, forces JSON response.
            options: Optional dict of Ollama runtime parameters.

        Returns:
            Generated assistant response content.
        """
        url = f"{self.base_url}/api/chat"
        gen_opts: dict[str, Any] = {
            "temperature": (
                temperature if temperature is not None else self.default_temperature
            ),
        }
        if options:
            gen_opts.update(options)

        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": gen_opts,
        }
        if format_json:
            payload["format"] = "json"

        try:
            with httpx.Client(timeout=float(self.timeout_seconds)) as client:
                resp = client.post(url, json=payload)
                if resp.status_code != 200:
                    raise OllamaResponseError(
                        f"Ollama chat failed (HTTP {resp.status_code}): {resp.text}"
                    )
                data = resp.json()
                msg = data.get("message", {})
                content = msg.get("content", "")
                if not content and "thinking" in msg:
                    content = msg.get("thinking", "")
                if "</think>" in content:
                    tail = content.split("</think>")[-1].strip()
                    if tail:
                        content = tail
                return content
        except httpx.RequestError as exc:
            logger.error("Ollama chat connection failed: %s", exc)
            raise OllamaConnectionError(
                f"Failed to connect to Ollama server at {self.base_url}."
            ) from exc
