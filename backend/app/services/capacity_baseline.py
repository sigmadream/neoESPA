from __future__ import annotations

import json
import os
import shutil
from datetime import UTC, datetime
from pathlib import Path

from .artifact_store import LocalArtifactStore


def _memory_bytes() -> int | None:
    try:
        pages = os.sysconf("SC_PHYS_PAGES")
        page_size = os.sysconf("SC_PAGE_SIZE")
        return int(pages * page_size)
    except AttributeError, OSError, ValueError:
        return None


def record_capacity_baseline(
    *,
    expected_students: int,
    max_concurrent_submissions: int,
    expected_term_submissions: int,
    root: Path | None = None,
) -> dict:
    if (
        min(
            expected_students,
            max_concurrent_submissions,
            expected_term_submissions,
        )
        < 1
    ):
        raise ValueError("Capacity planning inputs must be positive")
    bundle_root = (root or LocalArtifactStore().root).resolve()
    manifests = bundle_root / "manifests"
    manifests.mkdir(parents=True, exist_ok=True, mode=0o700)
    usage = shutil.disk_usage(bundle_root)
    baseline = {
        "recorded_at": datetime.now(UTC).isoformat(),
        "cpu_count": os.cpu_count(),
        "memory_bytes": _memory_bytes(),
        "disk_total_bytes": usage.total,
        "disk_free_bytes": usage.free,
        "expected_students": expected_students,
        "max_concurrent_submissions": max_concurrent_submissions,
        "expected_term_submissions": expected_term_submissions,
    }
    target = manifests / "capacity.json"
    target.write_text(
        json.dumps(baseline, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    target.chmod(0o600)
    return baseline
