from typing import Any, List, Optional
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.logging import get_logger
from app.schemas.errors import ErrorDetail, ErrorResponse

logger = get_logger("coverwise.errors")


class CoverWiseException(Exception):
    """Base application exception for CoverWise backend."""

    def __init__(self, message: str, code: str = "APPLICATION_ERROR", status_code: int = 400, details: Any = None):
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details
        super().__init__(message)


class ResourceNotFoundError(CoverWiseException):
    """Exception raised when a requested resource is not found."""

    def __init__(self, message: str = "Resource not found", details: Any = None):
        super().__init__(message=message, code="NOT_FOUND", status_code=status.HTTP_404_NOT_FOUND, details=details)


class UnauthorizedError(CoverWiseException):
    """Exception raised for unauthenticated requests."""

    def __init__(self, message: str = "Authentication required", details: Any = None):
        super().__init__(message=message, code="UNAUTHORIZED", status_code=status.HTTP_401_UNAUTHORIZED, details=details)


class ForbiddenError(CoverWiseException):
    """Exception raised for forbidden operations."""

    def __init__(self, message: str = "Access forbidden", details: Any = None):
        super().__init__(message=message, code="FORBIDDEN", status_code=status.HTTP_403_FORBIDDEN, details=details)


# In modern HTTP / Starlette standards, 422 is Unprocessable Content
HTTP_422_UNPROCESSABLE = getattr(status, "HTTP_422_UNPROCESSABLE_CONTENT", 422)


class ValidationAppError(CoverWiseException):
    """Exception raised for domain-level validation failures."""

    def __init__(self, message: str = "Validation failed", details: Any = None):
        super().__init__(message=message, code="VALIDATION_ERROR", status_code=HTTP_422_UNPROCESSABLE, details=details)


class DatabaseError(CoverWiseException):
    """Exception raised for internal database failures."""

    def __init__(self, message: str = "Database operation failed", details: Any = None):
        super().__init__(message=message, code="DATABASE_ERROR", status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, details=details)


def _map_http_status_to_code(status_code: int) -> str:
    """Map common HTTP status codes to standardized error code strings."""
    mapping = {
        400: "BAD_REQUEST",
        401: "UNAUTHORIZED",
        403: "FORBIDDEN",
        404: "NOT_FOUND",
        405: "METHOD_NOT_ALLOWED",
        409: "CONFLICT",
        422: "VALIDATION_ERROR",
        429: "TOO_MANY_REQUESTS",
        500: "INTERNAL_SERVER_ERROR",
        502: "BAD_GATEWAY",
        503: "SERVICE_UNAVAILABLE",
    }
    return mapping.get(status_code, f"HTTP_{status_code}")


def _get_request_id(request: Request) -> Optional[str]:
    """Extract request_id from request state or correlation headers."""
    return getattr(request.state, "request_id", None) or request.headers.get("X-Request-ID")


def register_error_handlers(app: FastAPI) -> None:
    """Register uniform error handlers for all exceptions."""

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        """Handle request parameter and body validation errors."""
        request_id = _get_request_id(request)
        sanitized_details: List[dict] = []
        for error in exc.errors():
            loc = " -> ".join(str(loc_item) for loc_item in error.get("loc", []))
            sanitized_details.append(
                {
                    "location": loc,
                    "message": error.get("msg", "Invalid value"),
                    "type": error.get("type", "value_error"),
                }
            )

        logger.warning(
            f"[{request_id}] Validation error on {request.method} {request.url.path}: {sanitized_details}"
        )

        message = "Request validation failed. Please check your request parameters."
        response_payload = ErrorResponse(
            code="VALIDATION_ERROR",
            message=message,
            details=sanitized_details,
            request_id=request_id,
            detail=message,
            error=ErrorDetail(
                code="VALIDATION_ERROR",
                message=message,
                details=sanitized_details,
                request_id=request_id,
            ),
        )
        return JSONResponse(
            status_code=HTTP_422_UNPROCESSABLE,
            content=response_payload.model_dump(),
            headers={"X-Request-ID": request_id} if request_id else None,
        )

    @app.exception_handler(CoverWiseException)
    async def coverwise_exception_handler(request: Request, exc: CoverWiseException) -> JSONResponse:
        """Handle domain-specific CoverWise application errors."""
        request_id = _get_request_id(request)
        logger.warning(
            f"[{request_id}] Application exception on {request.method} {request.url.path}: [{exc.code}] {exc.message}"
        )
        response_payload = ErrorResponse(
            code=exc.code,
            message=exc.message,
            details=exc.details,
            request_id=request_id,
            detail=exc.message,
            error=ErrorDetail(
                code=exc.code,
                message=exc.message,
                details=exc.details,
                request_id=request_id,
            ),
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=response_payload.model_dump(),
            headers={"X-Request-ID": request_id} if request_id else None,
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        """Handle standard HTTPExceptions (404, 401, 403, 413, 415, etc.)."""
        request_id = _get_request_id(request)
        code = _map_http_status_to_code(exc.status_code)
        message = str(exc.detail) if exc.detail else "An HTTP error occurred."

        if exc.status_code >= 500:
            logger.error(f"[{request_id}] HTTP {exc.status_code} on {request.method} {request.url.path}: {message}")
        else:
            logger.warning(f"[{request_id}] HTTP {exc.status_code} on {request.method} {request.url.path}: {message}")

        response_payload = ErrorResponse(
            code=code,
            message=message,
            details=None,
            request_id=request_id,
            detail=message,
            error=ErrorDetail(
                code=code,
                message=message,
                details=None,
                request_id=request_id,
            ),
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=response_payload.model_dump(),
            headers={"X-Request-ID": request_id} if request_id else None,
        )

    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        """Handle unhandled internal server exceptions without leaking stack traces or internal secrets."""
        request_id = _get_request_id(request)
        logger.error(
            f"[{request_id}] Unhandled internal server error on {request.method} {request.url.path}: {type(exc).__name__}: {str(exc)}",
            exc_info=True,
        )

        message = "An unexpected error occurred. Please try again later."
        response_payload = ErrorResponse(
            code="INTERNAL_SERVER_ERROR",
            message=message,
            details=None,
            request_id=request_id,
            detail="An unexpected internal server error occurred.",
            error=ErrorDetail(
                code="INTERNAL_SERVER_ERROR",
                message=message,
                details=None,
                request_id=request_id,
            ),
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=response_payload.model_dump(),
            headers={"X-Request-ID": request_id} if request_id else None,
        )
