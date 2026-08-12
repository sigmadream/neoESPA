import json

import pytest

from app.services.capacity_baseline import record_capacity_baseline


def test_capacity_baseline_records_host_and_workload_inputs(tmp_path):
    result = record_capacity_baseline(
        expected_students=120,
        max_concurrent_submissions=20,
        expected_term_submissions=50000,
        root=tmp_path,
    )
    stored = json.loads((tmp_path / "manifests/capacity.json").read_text())
    assert result["expected_students"] == 120
    assert stored["max_concurrent_submissions"] == 20
    assert stored["cpu_count"] is not None
    assert stored["disk_total_bytes"] > 0


def test_capacity_baseline_rejects_zero_assumptions(tmp_path):
    with pytest.raises(ValueError, match="positive"):
        record_capacity_baseline(
            expected_students=0,
            max_concurrent_submissions=1,
            expected_term_submissions=1,
            root=tmp_path,
        )
