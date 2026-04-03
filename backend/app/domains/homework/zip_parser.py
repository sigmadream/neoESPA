from __future__ import annotations

import io
import re
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO

from ...models.schemas import HomeworkTestCaseWrite

MAX_HOMEWORK_ARCHIVE_BYTES = 10 * 1024 * 1024
MAX_HOMEWORK_EXTRACTED_BYTES = 20 * 1024 * 1024
MAX_HOMEWORK_TESTCASE_PAIRS = 200

_WINDOWS_DRIVE_PATTERN = re.compile(r"^[A-Za-z]:")


class HomeworkZipValidationError(ValueError):
    pass


@dataclass(frozen=True)
class _ArchiveMember:
    name: str
    content: str


def parse_homework_testcase_archives(
    input_zip_stream: BinaryIO,
    output_zip_stream: BinaryIO,
) -> list[HomeworkTestCaseWrite]:
    input_members, extracted_size = _read_archive_members(
        input_zip_stream, archive_label="Input ZIP"
    )
    output_members, _ = _read_archive_members(
        output_zip_stream,
        archive_label="Output ZIP",
        extracted_size_so_far=extracted_size,
    )

    input_names = [member.name for member in input_members]
    output_names = [member.name for member in output_members]

    if not input_names or not output_names:
        raise HomeworkZipValidationError(
            "Testcase ZIP archives must contain at least one file pair"
        )

    if input_names != output_names:
        raise HomeworkZipValidationError(
            "Input and output ZIP archives must contain matching filenames"
        )

    if len(input_members) > MAX_HOMEWORK_TESTCASE_PAIRS:
        raise HomeworkZipValidationError(
            f"Testcase ZIP archives may contain at most {MAX_HOMEWORK_TESTCASE_PAIRS} file pairs"
        )

    return [
        HomeworkTestCaseWrite(
            name=input_member.name,
            input=input_member.content,
            expected_output=output_member.content,
        )
        for input_member, output_member in zip(
            input_members, output_members, strict=True
        )
    ]


def _read_archive_members(
    archive_stream: BinaryIO,
    *,
    archive_label: str,
    extracted_size_so_far: int = 0,
) -> tuple[list[_ArchiveMember], int]:
    # Try to check archive size via seek if possible
    try:
        archive_stream.seek(0, io.SEEK_END)
        archive_size = archive_stream.tell()
        archive_stream.seek(0)
        
        if archive_size > MAX_HOMEWORK_ARCHIVE_BYTES:
            raise HomeworkZipValidationError(
                f"{archive_label} exceeds {MAX_HOMEWORK_ARCHIVE_BYTES // (1024 * 1024)}MB archive size limit"
            )
    except (io.UnsupportedOperation, AttributeError):
        # Fallback: zipfile will handle large files, but we can't pre-check the archive size easily
        pass

    extracted_size = extracted_size_so_far
    members: list[_ArchiveMember] = []
    seen_names: set[str] = set()

    try:
        with zipfile.ZipFile(archive_stream) as archive:
            for info in archive.infolist():
                member_name = _validate_member_name(
                    info.filename, archive_label, is_directory=info.is_dir()
                )
                if member_name in seen_names:
                    raise HomeworkZipValidationError(
                        f"{archive_label} contains duplicate testcase name: {member_name}"
                    )

                extracted_size += info.file_size
                if extracted_size > MAX_HOMEWORK_EXTRACTED_BYTES:
                    raise HomeworkZipValidationError(
                        f"Combined extracted testcase size exceeds {MAX_HOMEWORK_EXTRACTED_BYTES // (1024 * 1024)}MB limit"
                    )

                try:
                    content = archive.read(info).decode("utf-8")
                except UnicodeDecodeError as error:
                    raise HomeworkZipValidationError(
                        f"{archive_label} contains non-UTF-8 testcase content: {member_name}"
                    ) from error

                seen_names.add(member_name)
                members.append(_ArchiveMember(name=member_name, content=content))
    except HomeworkZipValidationError:
        raise
    except (zipfile.BadZipFile, zipfile.LargeZipFile, OSError, RuntimeError) as error:
        raise HomeworkZipValidationError(
            f"{archive_label} is corrupt or unreadable"
        ) from error

    members.sort(key=lambda member: member.name)
    return members, extracted_size


def _validate_member_name(name: str, archive_label: str, *, is_directory: bool) -> str:
    safe_name = Path(name).name
    if (
        not name
        or is_directory
        or safe_name != name
        or name in {".", ".."}
        or ".." in name
        or "\\" in name
        or name.startswith(("/", "\\"))
        or _WINDOWS_DRIVE_PATTERN.match(name)
    ):
        raise HomeworkZipValidationError(
            f"{archive_label} contains unsupported member path: {name or '<empty>'}"
        )
    return name
