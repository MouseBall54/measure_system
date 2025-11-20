"""FastAPI application entrypoint."""

from __future__ import annotations

import json
import logging
from contextlib import asynccontextmanager
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
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

logger = logging.getLogger("measure_system")


def _configure_logging() -> None:
    log_dir = Path(settings.log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "error.log"
    root_logger = logging.getLogger()
    for handler in root_logger.handlers:
        if isinstance(handler, TimedRotatingFileHandler) and Path(handler.baseFilename) == log_file:
            return
    handler = TimedRotatingFileHandler(
        log_file,
        when="midnight",
        interval=1,
        backupCount=14,
        encoding="utf-8",
        utc=False,
    )
    handler.setLevel(logging.ERROR)
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
    root_logger.addHandler(handler)


_configure_logging()


def _extract_file_path_from_body(body: Any) -> str | None:
    if body is None:
        return None
    parsed = body
    if isinstance(body, (bytes, str)):
        try:
            parsed = json.loads(body)
        except (json.JSONDecodeError, TypeError):
            return None
    if not isinstance(parsed, dict):
        return None
    file_payload = parsed.get("file")
    if not isinstance(file_payload, dict):
        return None
    file_path = file_payload.get("file_path")
    return file_path if isinstance(file_path, str) else None


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    file_path = _extract_file_path_from_body(exc.body)
    if file_path:
        logger.error("422 validation error for file_path=%s: %s", file_path, exc.errors())
    else:
        logger.error("422 validation error (file_path unavailable): %s", exc.errors())
    return await request_validation_exception_handler(request, exc)


@app.get("/", include_in_schema=False)
async def root_redirect() -> RedirectResponse:
    """Redirect root to the interactive API docs."""

    return RedirectResponse(url="/docs")
