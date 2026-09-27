from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Backend health check status model."""

    status: str = Field(default="ok", description="Backend operational status")
    service: str = Field(default="coverwise-backend", description="Backend service identifier")
    environment: str = Field(..., description="Active runtime environment")
    version: str = Field(..., description="Application version")
