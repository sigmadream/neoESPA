import pytest
from app.domains.homework.helpers import (
    _normalize_artifact_metadata_payload,
    _validate_artifact_metadata_rule_name,
)


def test_validate_artifact_metadata_rule_name_invalid():
    with pytest.raises(
        ValueError, match="Unsupported artifact metadata rule name"
    ):
        _validate_artifact_metadata_rule_name("invalid_rule_name")


def test_normalize_artifact_metadata_payload_invalid():
    with pytest.raises(
        ValueError, match="Artifact metadata payload must be an object"
    ):
        _normalize_artifact_metadata_payload("not a dict")

    with pytest.raises(
        ValueError, match="Artifact metadata payload must include exactly"
    ):
        _normalize_artifact_metadata_payload({"original_name": "a.txt"})

    with pytest.raises(
        ValueError, match="original_name must be a non-empty string"
    ):
        _normalize_artifact_metadata_payload(
            {
                "original_name": "  ",
                "stored_relpath": "rel/path",
                "size_bytes": 10,
                "content_type": "text/plain",
            }
        )

    with pytest.raises(
        ValueError, match="stored_relpath must be a non-empty string"
    ):
        _normalize_artifact_metadata_payload(
            {
                "original_name": "test.txt",
                "stored_relpath": "",
                "size_bytes": 10,
                "content_type": "text/plain",
            }
        )

    with pytest.raises(
        ValueError, match="size_bytes must be a non-negative integer"
    ):
        _normalize_artifact_metadata_payload(
            {
                "original_name": "test.txt",
                "stored_relpath": "rel/path",
                "size_bytes": -1,
                "content_type": "text/plain",
            }
        )

    with pytest.raises(
        ValueError, match="content_type must be a string or null"
    ):
        _normalize_artifact_metadata_payload(
            {
                "original_name": "test.txt",
                "stored_relpath": "rel/path",
                "size_bytes": 100,
                "content_type": 123,
            }
        )
