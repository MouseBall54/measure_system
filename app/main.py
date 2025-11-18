"""FastAPI application entrypoint."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import RedirectResponse

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


@app.get("/", include_in_schema=False)
async def root_redirect() -> RedirectResponse:
    """Redirect root to the interactive API docs."""

    return RedirectResponse(url="/docs")
