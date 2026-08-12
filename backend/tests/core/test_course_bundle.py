import sqlite3
import pytest
from sqlmodel import Session, SQLModel, create_engine

from app.services.artifact_store import LocalArtifactStore
from app.services.course_bundle import CourseBundleService
from app.models.schemas import JudgeJob


def test_course_bundle_snapshot_manifest_and_verify(tmp_path):
    database = tmp_path / "source.sqlite3"
    connection = sqlite3.connect(database)
    connection.execute("CREATE TABLE sample (id INTEGER PRIMARY KEY, value TEXT)")
    connection.execute("INSERT INTO sample (value) VALUES ('preserved')")
    connection.commit()
    connection.close()
    store = LocalArtifactStore(tmp_path / "bundle")
    store.put_bytes(b"artifact")
    service = CourseBundleService(store)

    snapshot = service.create_snapshot(
        database,
        course_id="CS101",
        term="2026-fall",
        schema_version="0011_admin_bootstrap",
    )

    restored = sqlite3.connect(snapshot)
    assert restored.execute("SELECT value FROM sample").fetchone()[0] == "preserved"
    restored.close()
    assert service.verify() == []
    assert (store.root / "manifests" / "objects.jsonl").is_file()


def test_course_bundle_detects_checksum_mismatch(tmp_path):
    database = tmp_path / "source.sqlite3"
    sqlite3.connect(database).close()
    store = LocalArtifactStore(tmp_path / "bundle")
    artifact = store.put_bytes(b"original")
    service = CourseBundleService(store)
    service.create_snapshot(
        database,
        course_id="CS101",
        term="2026-fall",
        schema_version="test",
    )
    (store.root / artifact.relative_path).write_bytes(b"tampered")

    assert any("Checksum mismatch" in error for error in service.verify())


def test_course_bundle_restore_rehearsal_preserves_rows(tmp_path):
    database = tmp_path / "source.sqlite3"
    connection = sqlite3.connect(database)
    connection.execute("CREATE TABLE sample (id INTEGER PRIMARY KEY, value TEXT)")
    connection.executemany("INSERT INTO sample (value) VALUES (?)", [("one",), ("two",)])
    connection.commit()
    connection.close()
    service = CourseBundleService(LocalArtifactStore(tmp_path / "bundle"))
    service.create_snapshot(
        database, course_id="CS101", term="2026-fall", schema_version="test"
    )
    restored = tmp_path / "restored.sqlite3"
    counts = service.restore_snapshot(restored)
    connection = sqlite3.connect(restored)
    values = connection.execute("SELECT value FROM sample ORDER BY id").fetchall()
    connection.close()
    assert counts == {"sample": 2}
    assert values == [("one",), ("two",)]


def test_course_bundle_restore_refuses_unverified_or_existing_target(tmp_path):
    database = tmp_path / "source.sqlite3"
    sqlite3.connect(database).close()
    service = CourseBundleService(LocalArtifactStore(tmp_path / "bundle"))
    service.create_snapshot(database, course_id="CS101", term="2026", schema_version="test")
    target = tmp_path / "target.sqlite3"
    target.write_bytes(b"keep")
    try:
        service.restore_snapshot(target)
    except FileExistsError:
        pass
    else:
        raise AssertionError("existing restore target must require replace=True")
    assert target.read_bytes() == b"keep"


def test_operational_snapshot_refuses_active_queue_without_write_freeze(tmp_path):
    database = tmp_path / "course.sqlite3"
    engine = create_engine(f"sqlite:///{database}")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        session.add(JudgeJob(job_type="noop", payload_hash="x" * 64, status="queued"))
        session.commit()
        service = CourseBundleService(LocalArtifactStore(tmp_path / "bundle"))
        with pytest.raises(ValueError, match="Queue must be idle"):
            service.create_operational_snapshot(
                session, database, course_id="C", term="T", schema_version="test"
            )
        snapshot = service.create_operational_snapshot(
            session, database, course_id="C", term="T", schema_version="test",
            write_frozen=True,
        )
        assert snapshot.is_file()
    SQLModel.metadata.drop_all(engine)
