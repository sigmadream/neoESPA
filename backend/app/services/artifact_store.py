from __future__ import annotations

import hashlib
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO

from ..core.config import settings


MAX_ARTIFACT_BYTES = 50 * 1024 * 1024


class ArtifactValidationError(ValueError):
    pass


@dataclass(frozen=True)
class StoredArtifact:
    sha256: str
    relative_path: str
    size_bytes: int
    was_created: bool = False


class LocalArtifactStore:
    def __init__(self, root: Path | None = None):
        self.root = (root or settings.COURSE_BUNDLE_ROOT).resolve()
        self.objects_root = self.root / "objects" / "sha256"
        self.staging_root = self.root / "staging"

    def initialize(self) -> None:
        self.objects_root.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.staging_root.mkdir(parents=True, exist_ok=True, mode=0o700)
        if self.objects_root.stat().st_dev != self.staging_root.stat().st_dev:
            raise RuntimeError("Artifact staging and objects must use the same filesystem")

    def put_bytes(self, content: bytes) -> StoredArtifact:
        from io import BytesIO

        return self.put_stream(BytesIO(content))

    def put_stream(self, stream: BinaryIO, *, max_bytes: int = MAX_ARTIFACT_BYTES) -> StoredArtifact:
        self.initialize()
        digest = hashlib.sha256()
        size = 0
        fd, staging_name = tempfile.mkstemp(prefix="upload-", dir=self.staging_root)
        staging_path = Path(staging_name)
        try:
            with os.fdopen(fd, "wb") as target:
                while True:
                    chunk = stream.read(1024 * 1024)
                    if not chunk:
                        break
                    size += len(chunk)
                    if size > max_bytes:
                        raise ArtifactValidationError(
                            f"Artifact exceeds {max_bytes} byte limit"
                        )
                    digest.update(chunk)
                    target.write(chunk)
                target.flush()
                os.fsync(target.fileno())

            sha256 = digest.hexdigest()
            relative = Path("objects") / "sha256" / sha256[:2] / sha256
            destination = self.root / relative
            destination.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            was_created = not destination.exists()
            if destination.exists():
                staging_path.unlink()
            else:
                os.replace(staging_path, destination)
                destination.chmod(0o600)
            return StoredArtifact(sha256, relative.as_posix(), size, was_created)
        except Exception:
            staging_path.unlink(missing_ok=True)
            raise

    def discard_new(self, stored: StoredArtifact) -> None:
        """Remove an object created by a failed transaction, never a deduplicated object."""
        if not stored.was_created:
            return
        candidate = (self.root / stored.relative_path).resolve()
        if self.root in candidate.parents and candidate.is_file():
            candidate.unlink()

    def resolve(self, relative_path: str, expected_sha256: str | None = None) -> Path:
        candidate = (self.root / relative_path).resolve()
        if self.root not in candidate.parents:
            raise ArtifactValidationError("Artifact path escapes course bundle")
        if not candidate.is_file():
            raise FileNotFoundError(relative_path)
        if expected_sha256:
            actual = hashlib.sha256(candidate.read_bytes()).hexdigest()
            if actual != expected_sha256:
                raise ArtifactValidationError("Artifact checksum mismatch")
        return candidate
