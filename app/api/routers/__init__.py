"""Domain-specific routers bundled into a single APIRouter."""

from fastapi import APIRouter

from . import health, measurements


router = APIRouter()
router.include_router(health.router)
router.include_router(measurements.router)

__all__ = ["router"]
