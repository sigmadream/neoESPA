from __future__ import annotations

import os
from pathlib import Path


def resolve_support_dir(base_file: str | Path) -> Path:
    env_path = os.getenv("NEOESPA_SUPPORT_DIR")
    if env_path:
        candidate = Path(env_path).expanduser().resolve()
        if candidate.is_dir():
            return candidate

    resolved_file = Path(base_file).resolve()
    search_roots = [resolved_file.parent, *resolved_file.parents]

    for root in search_roots:
        candidate = root / "supportFiles"
        if candidate.is_dir():
            return candidate

    raise FileNotFoundError(
        f"Could not locate supportFiles directory from {resolved_file}"
    )
