"""Basic structural tests for FastAPI routers."""

from fastapi.routing import APIRoute

from app.api.routers import router


def test_router_contains_expected_paths() -> None:
    paths = {route.path for route in router.routes if isinstance(route, APIRoute)}
    assert "/health" in paths
    assert "/measurement-results/" in paths


def test_routes_have_tags() -> None:
    tagged_routes = [route for route in router.routes if isinstance(route, APIRoute)]
    assert all(route.tags for route in tagged_routes)
