"""Domain-specific routers bundled into a single APIRouter."""

from fastapi import APIRouter

from . import health, measurement_results


router = APIRouter()
router.include_router(health.router)
router.include_router(measurement_results.router)

__all__ = ["router"]
