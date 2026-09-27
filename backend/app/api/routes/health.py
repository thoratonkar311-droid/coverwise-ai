from fastapi import APIRouter
from app.core.config import settings
from app.schemas.health import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse, tags=["Health"])
async def get_health() -> HealthResponse:
    """Return backend operational status and service information without exposing sensitive configuration."""
    return HealthResponse(
        status="ok",
        service="coverwise-backend",
        environment=settings.ENVIRONMENT,
        version=settings.VERSION,
    )
