from datetime import UTC, datetime, timedelta

from sqlmodel import select

from app.core.compression import compress_text, decompress_text
from app.models.schemas import CodeSnapshot, Homework
from app.services.snapshot_retention_service import snapshot_retention_service


def _create_homework(session, num):
    now = datetime.now(UTC)
    homework = Homework(
        num=num,
        title=f"Retention Homework {num}",
        intro="Retention test",
        codeName=f"retention_{num}",
        created_at=now,
        updated_at=now,
    )
    session.add(homework)
    session.commit()
    session.refresh(homework)
    return homework


def _create_snapshot(session, *, homework_num, user_id, code_text, created_at, snapshot_type="auto_save"):
    snapshot = CodeSnapshot(
        homework_num=homework_num,
        user_id=user_id,
        language="python",
        code_text=compress_text(code_text),
        snapshot_type=snapshot_type,
        created_at=created_at,
    )
    session.add(snapshot)
    session.commit()
    session.refresh(snapshot)
    return snapshot


def test_prune_code_snapshots_deletes_only_expired_entries(session, create_user):
    now = datetime.now(UTC)
    _create_homework(session, 101)
    create_user("retention-student-1", 20240101, "password")

    old_snapshot = _create_snapshot(
        session,
        homework_num=101,
        user_id="retention-student-1",
        code_text="print('expired')",
        created_at=now - timedelta(days=10),
    )
    recent_snapshot = _create_snapshot(
        session,
        homework_num=101,
        user_id="retention-student-1",
        code_text="print('recent')",
        created_at=now - timedelta(days=1),
    )

    report = snapshot_retention_service.prune_code_snapshots(
        session,
        older_than=now - timedelta(days=7),
        keep_latest_per_scope=0,
    )

    remaining_snapshots = session.exec(select(CodeSnapshot).order_by(CodeSnapshot.id.asc())).all()

    assert report["deleted_count"] == 1
    assert report["deleted_ids"] == [old_snapshot.id]
    assert [snapshot.id for snapshot in remaining_snapshots] == [recent_snapshot.id]


def test_prune_code_snapshots_keeps_latest_n_even_if_they_are_old(session, create_user):
    now = datetime.now(UTC)
    _create_homework(session, 102)
    create_user("retention-student-2", 20240102, "password")

    oldest_snapshot = _create_snapshot(
        session,
        homework_num=102,
        user_id="retention-student-2",
        code_text="print('oldest')",
        created_at=now - timedelta(days=12),
    )
    middle_snapshot = _create_snapshot(
        session,
        homework_num=102,
        user_id="retention-student-2",
        code_text="print('middle')",
        created_at=now - timedelta(days=11),
    )
    newest_old_snapshot = _create_snapshot(
        session,
        homework_num=102,
        user_id="retention-student-2",
        code_text="print('newest-old')",
        created_at=now - timedelta(days=10),
    )

    report = snapshot_retention_service.prune_code_snapshots(
        session,
        older_than=now - timedelta(days=7),
        keep_latest_per_scope=2,
    )

    remaining_snapshots = session.exec(
        select(CodeSnapshot).order_by(CodeSnapshot.created_at.desc(), CodeSnapshot.id.desc())
    ).all()

    assert report["deleted_ids"] == [oldest_snapshot.id]
    assert [snapshot.id for snapshot in remaining_snapshots] == [newest_old_snapshot.id, middle_snapshot.id]


def test_prune_code_snapshots_archive_keeps_restorable_payload(session, create_user):
    now = datetime.now(UTC)
    _create_homework(session, 103)
    create_user("retention-student-3", 20240103, "password")

    snapshot = _create_snapshot(
        session,
        homework_num=103,
        user_id="retention-student-3",
        code_text="print('archive me')\nprint('still restorable')",
        created_at=now - timedelta(days=14),
    )

    report = snapshot_retention_service.prune_code_snapshots(
        session,
        older_than=now - timedelta(days=7),
        keep_latest_per_scope=0,
        archive=True,
    )

    remaining_snapshots = session.exec(select(CodeSnapshot)).all()
    archived_snapshots = report["archived_snapshots"]

    assert report["deleted_ids"] == [snapshot.id]
    assert remaining_snapshots == []
    assert len(archived_snapshots) == 1
    assert archived_snapshots[0]["id"] == snapshot.id
    assert archived_snapshots[0]["code_text"] == snapshot.code_text
    assert (
        decompress_text(archived_snapshots[0]["code_text"])
        == "print('archive me')\nprint('still restorable')"
    )


def test_prune_code_snapshots_does_not_remove_other_users_latest_snapshot(session, create_user):
    now = datetime.now(UTC)
    _create_homework(session, 104)
    create_user("retention-student-4", 20240104, "password")
    create_user("retention-student-5", 20240105, "password")

    _create_snapshot(
        session,
        homework_num=104,
        user_id="retention-student-4",
        code_text="print('user4 oldest')",
        created_at=now - timedelta(days=13),
    )
    user4_latest = _create_snapshot(
        session,
        homework_num=104,
        user_id="retention-student-4",
        code_text="print('user4 latest old')",
        created_at=now - timedelta(days=12),
    )
    user5_latest = _create_snapshot(
        session,
        homework_num=104,
        user_id="retention-student-5",
        code_text="print('user5 latest old')",
        created_at=now - timedelta(days=11),
    )

    report = snapshot_retention_service.prune_code_snapshots(
        session,
        older_than=now - timedelta(days=7),
        keep_latest_per_scope=1,
    )

    remaining_snapshots = session.exec(
        select(CodeSnapshot).order_by(CodeSnapshot.user_id.asc(), CodeSnapshot.created_at.desc())
    ).all()

    assert report["deleted_count"] == 1
    assert [snapshot.id for snapshot in remaining_snapshots] == [user4_latest.id, user5_latest.id]
    assert [decompress_text(snapshot.code_text) for snapshot in remaining_snapshots] == [
        "print('user4 latest old')",
        "print('user5 latest old')",
    ]
