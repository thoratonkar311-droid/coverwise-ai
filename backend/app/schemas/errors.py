from typing import Any, Optional
from pydantic import BaseModel, ConfigDict, Field


class ErrorDetail(BaseModel):
    """Standard structured error details."""

    model_config = ConfigDict(extra="ignore")

    code: str = Field(..., description="Standard machine-readable error code")
    message: str = Field(..., description="Human-readable error summary")
    details: Optional[Any] = Field(
        None, description="Optional granular error details or field-level validation errors"
    )
    request_id: Optional[str] = Field(None, description="Unique correlation / request identifier")


class ErrorResponse(BaseModel):
    """Consistent API error response structure conforming to prompt specifications."""

    model_config = ConfigDict(extra="ignore")

    code: str = Field(..., description="Standard machine-readable error code")
    message: str = Field(..., description="Human-readable error summary")
    details: Optional[Any] = Field(
        None, description="Optional granular error details or field-level validation errors"
    )
    request_id: Optional[str] = Field(None, description="Unique correlation / request identifier")

    # Compatibility fields for legacy client and existing test compatibility
    detail: Optional[str] = Field(None, description="Standard error summary for client compatibility")
    error: Optional[ErrorDetail] = Field(None, description="Nested structured error object")
