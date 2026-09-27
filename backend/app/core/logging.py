import logging
import sys
import time
from typing import Callable
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

SENSITIVE_PATTERNS = [
    "password",
    "secret",
    "secret_key",
    "token",
    "api_key",
    "authorization",
    "bearer",
    "credential",
]


class SensitiveDataFilter(logging.Filter):
    """Filter that masks sensitive data such as passwords, API keys, and secrets."""

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            lower_msg = record.msg.lower()
            for pattern in SENSITIVE_PATTERNS:
                if f"{pattern}=" in lower_msg or f'"{pattern}"' in lower_msg or f"'{pattern}'" in lower_msg:
                    record.msg = "[REDACTED: Sensitive Credentials]"
                    break
        return True


def setup_logging(log_level: str = "INFO") -> logging.Logger:
    """Initialize structured logging for CoverWise backend."""
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)

    log_format = (
        "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s"
    )
    date_format = "%Y-%m-%d %H:%M:%S"

    formatter = logging.Formatter(fmt=log_format, datefmt=date_format)

    # Stream handler writing to stdout
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    handler.addFilter(SensitiveDataFilter())

    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)

    # Avoid duplicate handlers if setup_logging is called multiple times
    if not root_logger.handlers:
        root_logger.addHandler(handler)
    else:
        root_logger.handlers = [handler]

    app_logger = logging.getLogger("coverwise")
    app_logger.setLevel(numeric_level)
    return app_logger


def get_logger(name: str = "coverwise") -> logging.Logger:
    """Retrieve an application logger by name."""
    return logging.getLogger(name)


import uuid


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for structured HTTP request and response logging with request correlation IDs."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        logger = get_logger("coverwise.requests")
        start_time = time.perf_counter()
        client_ip = request.client.host if request.client else "unknown"
        method = request.method
        path = request.url.path

        # Correlation request_id from header or freshly generated UUID
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.state.request_id = request_id

        try:
            response = await call_next(request)
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            status_code = response.status_code

            log_msg = f"[{request_id}] {method} {path} - {status_code} ({duration_ms}ms) [client: {client_ip}]"

            if status_code >= 500:
                logger.error(log_msg)
            elif status_code >= 400:
                logger.warning(log_msg)
            else:
                logger.info(log_msg)

            response.headers["X-Request-ID"] = request_id
            return response
        except Exception as exc:
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            logger.error(
                f"[{request_id}] {method} {path} - FAILED ({duration_ms}ms) [client: {client_ip}] - Error: {type(exc).__name__}: {str(exc)}",
                exc_info=True,
            )
            raise
