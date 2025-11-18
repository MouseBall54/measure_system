"""Domain-specific routers bundled into a single APIRouter."""

from fastapi import APIRouter

from . import files, health, raw_measurements, stat_measurements


router = APIRouter()
router.include_router(health.router)
router.include_router(files.router)
router.include_router(raw_measurements.router)
router.include_router(stat_measurements.router)

__all__ = ["router"]
