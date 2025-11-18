"""FastAPI application entrypoint."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from .api import router
from .core import engine, settings
from .models import Base


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Auto create tables for the prototype phase. Swap with Alembic later.
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.include_router(router)
