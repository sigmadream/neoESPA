from __future__ import annotations

import json
import zipfile
import stat
from dataclasses import dataclass
from io import BytesIO
from pathlib import PurePosixPath


MAX_PACKAGE_BYTES = 50 * 1024 * 1024
MAX_EXPANDED_BYTES = 200 * 1024 * 1024
MAX_FILES = 2000


class ProblemPackageError(ValueError):
    pass


@dataclass(frozen=True)
class PackageCase:
    name: str
    position: int
    score: float
    is_sample: bool
    input_name: str
    output_name: str
    input_content: bytes
    output_content: bytes


def read_limited_package(stream) -> bytes:
    chunks: list[bytes] = []
    size = 0
    while True:
        chunk = stream.read(1024 * 1024)
        if not chunk:
            break
        size += len(chunk)
        if size > MAX_PACKAGE_BYTES:
            raise ProblemPackageError("Problem package exceeds the upload limit")
        chunks.append(chunk)
    return b"".join(chunks)


def parse_problem_package(content: bytes) -> list[PackageCase]:
    if len(content) > MAX_PACKAGE_BYTES:
        raise ProblemPackageError("Problem package exceeds the upload limit")
    try:
        archive = zipfile.ZipFile(BytesIO(content))
    except zipfile.BadZipFile as error:
        raise ProblemPackageError("Problem package is not a valid ZIP") from error
    with archive:
        infos = [info for info in archive.infolist() if not info.is_dir()]
        if len(infos) > MAX_FILES:
            raise ProblemPackageError("Problem package contains too many files")
        if sum(info.file_size for info in infos) > MAX_EXPANDED_BYTES:
            raise ProblemPackageError("Expanded problem package is too large")
        names: set[str] = set()
        for info in infos:
            path = PurePosixPath(info.filename)
            if path.is_absolute() or ".." in path.parts or "\\" in info.filename:
                raise ProblemPackageError("Problem package contains an unsafe path")
            unix_mode = info.external_attr >> 16
            if stat.S_ISLNK(unix_mode):
                raise ProblemPackageError("Problem package cannot contain symbolic links")
            if info.filename in names:
                raise ProblemPackageError("Problem package contains duplicate paths")
            names.add(info.filename)
        if "manifest.json" not in names:
            raise ProblemPackageError("manifest.json is required")
        try:
            manifest = json.loads(archive.read("manifest.json"))
            raw_cases = manifest["testcases"]
        except (KeyError, TypeError, ValueError, UnicodeDecodeError) as error:
            raise ProblemPackageError("manifest.json is invalid") from error
        if not isinstance(raw_cases, list) or not raw_cases:
            raise ProblemPackageError("manifest testcases must be a non-empty list")
        cases: list[PackageCase] = []
        case_names: set[str] = set()
        positions: set[int] = set()
        for raw in raw_cases:
            try:
                name = str(raw["name"]).strip()
                position = int(raw["position"])
                score = float(raw.get("score", 0))
                input_name = str(raw["input"])
                output_name = str(raw["output"])
                is_sample = bool(raw.get("sample", False))
            except (KeyError, TypeError, ValueError) as error:
                raise ProblemPackageError("Testcase manifest entry is invalid") from error
            if not name or name in case_names or position < 1 or position in positions:
                raise ProblemPackageError("Testcase names and positive positions must be unique")
            if score < 0 or input_name not in names or output_name not in names:
                raise ProblemPackageError("Testcase files or score are invalid")
            input_content = archive.read(input_name)
            output_content = archive.read(output_name)
            if not input_content or not output_content:
                raise ProblemPackageError("Testcase input and output files cannot be empty")
            case_names.add(name)
            positions.add(position)
            cases.append(
                PackageCase(
                    name, position, score, is_sample, input_name, output_name,
                    input_content, output_content,
                )
            )
        return cases
