from pathlib import Path

from app.core.support_files import resolve_support_dir


def test_resolve_support_dir_walks_up_nested_service_path(tmp_path: Path):
    root = tmp_path / "app"
    support_dir = root / "supportFiles"
    support_dir.mkdir(parents=True)
    (support_dir / "week_rules.json").write_text("{}", encoding="utf-8")

    service_file = root / "app" / "services" / "lint_pipeline.py"
    service_file.parent.mkdir(parents=True)
    service_file.write_text("# placeholder", encoding="utf-8")

    assert resolve_support_dir(service_file) == support_dir
