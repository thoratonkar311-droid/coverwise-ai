"""API route handlers."""

from app.api.routes.analyses import router as analyses_router
from app.api.routes.health import router as health_router
from app.api.routes.policies import router as policies_router
from app.api.routes.simulations import router as simulations_router
from app.api.routes.treatments import router as treatments_router

__all__ = [
    "analyses_router",
    "health_router",
    "policies_router",
    "simulations_router",
    "treatments_router",
]
