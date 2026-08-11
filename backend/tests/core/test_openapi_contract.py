import re
from pathlib import Path

from app.main import app
from app.services.openapi_contract import breaking_changes, canonical_openapi


def _normalize_path(path: str) -> str:
    return re.sub(r"\{[^}]+\}", "{}", path)


def test_api_markdown_only_documents_real_routes():
    markdown = Path("API.md").read_text(encoding="utf-8")
    documented = {
        (method, _normalize_path(path))
        for method, path in re.findall(
            r"\| (GET|POST|PATCH|PUT|DELETE) \| `([^`]+)`", markdown
        )
    }
    actual = {
        (method, _normalize_path(route.path))
        for route in app.routes
        for method in getattr(route, "methods", set())
    }
    assert documented <= actual


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
