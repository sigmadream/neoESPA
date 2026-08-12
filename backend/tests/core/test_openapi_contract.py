import re
from pathlib import Path

from fastapi.routing import APIWebSocketRoute

from app.main import app
from app.services.openapi_contract import breaking_changes, canonical_openapi

HTTP_METHODS = {"GET", "POST", "PUT", "PATCH", "DELETE"}

# FastAPI generates these; they are not part of the API surface and vanish when
# docs_url/openapi_url are disabled, so neither side of the comparison may
# depend on them. API.md still lists them for readers.
FRAMEWORK_PATHS = {"/docs", "/docs/oauth2-redirect", "/redoc", "/openapi.json"}


def _documented_routes() -> set[tuple[str, str]]:
    markdown = Path("API.md").read_text(encoding="utf-8")
    return {
        (method, path)
        for method, path in re.findall(
            r"\| (GET|POST|PATCH|PUT|DELETE|WS) \| `([^`]+)`", markdown
        )
        if path not in FRAMEWORK_PATHS
    }


def _actual_routes() -> set[tuple[str, str]]:
    routes: set[tuple[str, str]] = set()
    for route in app.routes:
        if route.path in FRAMEWORK_PATHS:
            continue
        if isinstance(route, APIWebSocketRoute):
            routes.add(("WS", route.path))
            continue
        for method in (getattr(route, "methods", None) or set()) & HTTP_METHODS:
            routes.add((method, route.path))
    return routes


def test_api_markdown_documents_every_real_route_exactly():
    documented = _documented_routes()
    actual = _actual_routes()
    undocumented = sorted(actual - documented)
    stale = sorted(documented - actual)
    assert (
        not undocumented
    ), f"API.md is missing registered routes: {undocumented}"
    assert (
        not stale
    ), f"API.md documents routes that are not registered: {stale}"


def test_openapi_contract_detects_removed_operation_and_schema():
    baseline = {
        "openapi": "3.1.0",
        "paths": {"/api/items": {"get": {"responses": {"200": {}}}}},
        "components": {"schemas": {"Item": {"required": ["id"]}}},
    }
    current = {"openapi": "3.1.0", "paths": {}, "components": {"schemas": {}}}
    errors = breaking_changes(baseline, current)
    assert "removed path: /api/items" in errors
    assert "removed schema: Item" in errors


def test_canonical_openapi_is_stable():
    first = canonical_openapi(app.openapi())
    second = canonical_openapi(app.openapi())
    assert first == second
    assert first.endswith("\n")
