"""API module for endpoints and routing."""

from fastapi import APIRouter
from app.api.routes.analyses import router as analyses_router
from app.api.routes.auth import router as auth_router
from app.api.routes.conversations import router as conversations_router
from app.api.routes.coverage import router as coverage_router
from app.api.routes.dashboard import router as dashboard_router
from app.api.routes.health import router as health_router
from app.api.routes.policies import router as policies_router
from app.api.routes.simulations import router as simulations_router
from app.api.routes.treatment_estimates import router as treatment_estimates_router
from app.api.routes.treatments import router as treatments_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(auth_router)
api_router.include_router(policies_router)
api_router.include_router(analyses_router)
api_router.include_router(simulations_router)
api_router.include_router(treatments_router)
api_router.include_router(dashboard_router)
api_router.include_router(coverage_router)
api_router.include_router(conversations_router)
api_router.include_router(treatment_estimates_router)

__all__ = ["api_router"]
