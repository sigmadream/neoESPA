import json
import zipfile
import stat
from io import BytesIO

import pytest

from app.services.problem_package import ProblemPackageError, parse_problem_package


def _package(manifest: dict, files: dict[str, bytes]) -> bytes:
    target = BytesIO()
    with zipfile.ZipFile(target, "w") as archive:
        archive.writestr("manifest.json", json.dumps(manifest))
        for name, content in files.items():
            archive.writestr(name, content)
    return target.getvalue()


def test_parse_problem_package_pairs_manifest_files():
    content = _package(
        {"testcases": [{"name": "sample", "position": 1, "score": 100,
                         "sample": True, "input": "data/1.in", "output": "data/1.out"}]},
        {"data/1.in": b"1\n", "data/1.out": b"2\n"},
    )
    cases = parse_problem_package(content)
    assert len(cases) == 1
    assert cases[0].name == "sample"
    assert cases[0].input_content == b"1\n"


def test_parse_problem_package_rejects_missing_pair():
    content = _package(
        {"testcases": [{"name": "broken", "position": 1,
                         "input": "1.in", "output": "1.out"}]},
        {"1.in": b"1\n"},
    )
    with pytest.raises(ProblemPackageError, match="files or score"):
        parse_problem_package(content)


def test_parse_problem_package_rejects_path_traversal():
    content = _package({"testcases": []}, {"../escape": b"bad"})
    with pytest.raises(ProblemPackageError, match="unsafe path"):
        parse_problem_package(content)


def test_parse_problem_package_rejects_symlink():
    target = BytesIO()
    with zipfile.ZipFile(target, "w") as archive:
        archive.writestr("manifest.json", '{"testcases": []}')
        link = zipfile.ZipInfo("linked-input")
        link.create_system = 3
        link.external_attr = (stat.S_IFLNK | 0o777) << 16
        archive.writestr(link, "outside")
    with pytest.raises(ProblemPackageError, match="symbolic links"):
        parse_problem_package(target.getvalue())
