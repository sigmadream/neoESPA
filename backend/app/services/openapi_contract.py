from __future__ import annotations

import json
from pathlib import Path
from typing import Any

HTTP_METHODS = {"get", "post", "put", "patch", "delete", "options", "head"}


def canonical_openapi(schema: dict[str, Any]) -> str:
    return (
        json.dumps(schema, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    )


def breaking_changes(
    baseline: dict[str, Any], current: dict[str, Any]
) -> list[str]:
    errors: list[str] = []
    current_paths = current.get("paths", {})
    for path, baseline_path in baseline.get("paths", {}).items():
        if path not in current_paths:
            errors.append(f"removed path: {path}")
            continue
        for method, operation in baseline_path.items():
            if method.lower() not in HTTP_METHODS:
                continue
            current_operation = current_paths[path].get(method)
            if current_operation is None:
                errors.append(f"removed operation: {method.upper()} {path}")
                continue
            baseline_responses = operation.get("responses", {})
            current_responses = current_operation.get("responses", {})
            for response_code in baseline_responses:
                if response_code not in current_responses:
                    errors.append(
                        f"removed response {response_code}: {method.upper()} {path}"
                    )
            baseline_parameters = {
                (item.get("in"), item.get("name")): item
                for item in operation.get("parameters", [])
            }
            current_parameters = {
                (item.get("in"), item.get("name")): item
                for item in current_operation.get("parameters", [])
            }
            for key, parameter in baseline_parameters.items():
                if parameter.get("required") and key not in current_parameters:
                    errors.append(
                        f"removed required parameter {key[1]}: {method.upper()} {path}"
                    )
    baseline_schemas = baseline.get("components", {}).get("schemas", {})
    current_schemas = current.get("components", {}).get("schemas", {})
    for name, schema in baseline_schemas.items():
        if name not in current_schemas:
            errors.append(f"removed schema: {name}")
            continue
        current_required = set(current_schemas[name].get("required", []))
        for field in schema.get("required", []):
            if field not in current_required:
                errors.append(f"removed required field: {name}.{field}")
    return errors


def load_schema(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise ValueError(f"Cannot read OpenAPI schema: {path}") from error
    if (
        not isinstance(value, dict)
        or "openapi" not in value
        or "paths" not in value
    ):
        raise ValueError(f"Not an OpenAPI schema: {path}")
    return value
