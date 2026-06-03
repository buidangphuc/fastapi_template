from fastapi import APIRouter

from app.api.legacy.router import router as legacy_router
from app.api.v1.health.router import router as health_router
from app.core.config import Settings


def build_api_router(settings: Settings) -> APIRouter:
    router = APIRouter()
    router.include_router(health_router)
    router.include_router(health_router, prefix=settings.API_V1_PREFIX)
    # router.include_router(completions_router, prefix=settings.API_V1_PREFIX)
    # Legacy DGL-compat surface: byte-compatible paths under /api/v1, public
    # (no bearer), legacy envelope. Mounted only when the Mongo-backed domain
    # is enabled so the default platform app is unaffected.
    if settings.MONGO_ENABLED:
        router.include_router(legacy_router, prefix=settings.API_V1_PREFIX)
    return router
