from app.models.schemas import SubmissionFile
from app.services.artifact_store import LocalArtifactStore
from app.services.legacy_artifact_backfill import LegacyArtifactBackfillService


def test_legacy_submission_artifact_backfill_is_verified_and_idempotent(
    session, tmp_path, create_user, create_homework, create_submission
):
    create_user("legacy-user", 701)
    create_homework(1, "Legacy")
    legacy_root = tmp_path / "legacy"
    legacy_root.mkdir()
    source = legacy_root / "submission.c"
    source.write_bytes(b"int main(void) { return 0; }")
    submission = create_submission(
        homework_num=1, user_id="legacy-user", language="c", storage_path="submission.c"
    )
    submission_file = SubmissionFile(
        submission_id=submission.id or 0, artifact_kind="source", file_name="submission.c",
        storage_path="submission.c",
    )
    session.add(submission_file)
    session.commit()
    store = LocalArtifactStore(tmp_path / "bundle")
    service = LegacyArtifactBackfillService(store=store, legacy_root=legacy_root)
    first = service.run(session)
    second = service.run(session)
    session.refresh(submission)
    session.refresh(submission_file)
    assert first.migrated == 2
    assert second.already_migrated == 2
    assert submission.legacy_storage_path == "submission.c"
    assert submission.legacy_storage_status == "held"
    assert submission.storage_sha256 == submission_file.storage_sha256
    assert store.resolve(submission.storage_path, submission.storage_sha256).read_bytes() == source.read_bytes()
    assert source.is_file()
