from fastapi import APIRouter
from app.api.routes.health import router as health_router
from app.api.routes.simulations import router as simulations_router
from app.api.routes.assessments import router as assessments_router
from app.api.routes.policies import router as policies_router
from app.api.routes.zones import router as zones_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(simulations_router)
api_router.include_router(assessments_router)
api_router.include_router(policies_router)
api_router.include_router(zones_router)

__all__ = [
    "api_router",
    "health_router",
    "simulations_router",
    "assessments_router",
    "policies_router",
    "zones_router",
]
