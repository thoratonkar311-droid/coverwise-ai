import os
import sys
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Ensure repository root is on sys.path so 'ai' package can be resolved in containerized/cloud environments
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from app.api import api_router
from app.core.config import settings
from app.core.errors import register_error_handlers
from app.core.logging import RequestLoggingMiddleware, get_logger, setup_logging

# Configure structured logging
setup_logging(log_level=settings.LOG_LEVEL)
logger = get_logger("coverwise.main")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Lifespan event context manager for startup and shutdown procedures."""
    logger.info(
        f"Starting {settings.PROJECT_NAME} [Environment: {settings.ENVIRONMENT}] [Version: {settings.VERSION}]"
    )
    yield
    logger.info(f"Shutting down {settings.PROJECT_NAME}")


def create_application() -> FastAPI:
    """Instantiate and configure the FastAPI application."""
    app = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.VERSION,
        docs_url="/docs" if not settings.is_production else None,
        redoc_url="/redoc" if not settings.is_production else None,
        openapi_url="/openapi.json" if not settings.is_production else None,
        lifespan=lifespan,
    )

    # Structured request/response logging middleware
    app.add_middleware(RequestLoggingMiddleware)

    # CORS configuration for frontend
    allowed_origins = list(settings.ALLOWED_ORIGINS)
    if settings.is_development:
        dev_origins = ["http://localhost:3000", "http://127.0.0.1:3000"]
        for origin in dev_origins:
            if origin not in allowed_origins:
                allowed_origins.append(origin)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )

    # Uniform error handlers
    register_error_handlers(app)

    # Mount API routes under /api
    app.include_router(api_router, prefix=settings.API_V1_STR)
    # Also support direct root routes (e.g. /dashboard, /analyze, /simulator, /coverage)
    app.include_router(api_router, include_in_schema=False)

    return app


app = create_application()
