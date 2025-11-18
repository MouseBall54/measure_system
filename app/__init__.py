"""FastAPI application package for the Measure System server."""

from .main import app  # re-export for `uvicorn app:app`

__all__ = ["app"]
