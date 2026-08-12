from datetime import UTC

from sqlmodel import select

from ..models.schemas import CodeSnapshot


def _as_utc_naive(value):
    if value.tzinfo is None:
        return value
    return value.astimezone(UTC).replace(tzinfo=None)


class SnapshotRetentionService:
    def prune_code_snapshots(
        self,
        session,
        *,
        older_than,
        keep_latest_per_scope=1,
        archive=False,
    ):
        keep_latest_per_scope = max(int(keep_latest_per_scope), 0)
        snapshots = session.exec(
            select(CodeSnapshot).order_by(
                CodeSnapshot.homework_num.asc(),
                CodeSnapshot.user_id.asc(),
                CodeSnapshot.created_at.desc(),
                CodeSnapshot.id.desc(),
            )
        ).all()

        kept_counts = {}
        deleted_ids = []
        archived_snapshots = []

        for snapshot in snapshots:
            scope = (snapshot.homework_num, snapshot.user_id)
            kept_count = kept_counts.get(scope, 0)
            is_within_retention_window = _as_utc_naive(
                snapshot.created_at
            ) >= _as_utc_naive(older_than)
            should_keep_for_scope = kept_count < keep_latest_per_scope

            if is_within_retention_window or should_keep_for_scope:
                kept_counts[scope] = kept_count + 1
                continue

            if archive:
                archived_snapshots.append(self._build_archive_entry(snapshot))

            if snapshot.id is not None:
                deleted_ids.append(snapshot.id)
            session.delete(snapshot)

        session.commit()
        return {
            "deleted_count": len(deleted_ids),
            "deleted_ids": deleted_ids,
            "archived_snapshots": archived_snapshots,
        }

    def _build_archive_entry(self, snapshot):
        return {
            "id": snapshot.id,
            "homework_num": snapshot.homework_num,
            "user_id": snapshot.user_id,
            "language": snapshot.language,
            "code_text": snapshot.code_text,
            "snapshot_type": snapshot.snapshot_type,
            "created_at": snapshot.created_at.isoformat(),
        }


snapshot_retention_service = SnapshotRetentionService()
