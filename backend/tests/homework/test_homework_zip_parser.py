import io
import zipfile

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from app.domains.homework.zip_parser import (
    HomeworkZipValidationError,
    parse_homework_testcase_archives,
)

def _build_zip(members):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, content in members:
            archive.writestr(name, content)
    return buffer.getvalue()

def test_zip_parser_happy_path():
    input_zip = _build_zip([("a.txt", b"1\n"), ("b.txt", b"2\n")])
    output_zip = _build_zip([("a.txt", b"out1\n"), ("b.txt", b"out2\n")])

    testcases = parse_homework_testcase_archives(io.BytesIO(input_zip), io.BytesIO(output_zip))
    
    assert len(testcases) == 2
    assert testcases[0].name == "a.txt"
    assert testcases[0].input == "1\n"
    assert testcases[0].expected_output == "out1\n"


@settings(max_examples=20, deadline=None)
@given(
    pairs=st.dictionaries(
        keys=st.text(
            alphabet="abcdefghijklmnopqrstuvwxyz0123456789",
            min_size=1,
            max_size=8,
        ).map(lambda stem: f"{stem}.txt"),
        values=st.tuples(
            st.text(alphabet="abcxyz0123 \n안녕", min_size=0, max_size=20),
            st.text(alphabet="rstuvw4567 \n세계", min_size=0, max_size=20),
        ),
        min_size=1,
        max_size=6,
    )
)
def test_zip_parser_matches_pairs_independent_of_archive_member_order(pairs):
    input_zip = _build_zip(
        [(name, input_text.encode("utf-8")) for name, (input_text, _) in pairs.items()]
    )
    output_zip = _build_zip(
        [
            (name, output_text.encode("utf-8"))
            for name, (_, output_text) in reversed(list(pairs.items()))
        ]
    )

    testcases = parse_homework_testcase_archives(io.BytesIO(input_zip), io.BytesIO(output_zip))

    assert [testcase.name for testcase in testcases] == sorted(pairs)
    assert {
        testcase.name: (testcase.input, testcase.expected_output)
        for testcase in testcases
    } == pairs

def test_zip_parser_mismatched_filenames():
    input_zip = _build_zip([("a.txt", b"1")])
    output_zip = _build_zip([("b.txt", b"1")])

    with pytest.raises(HomeworkZipValidationError) as exc:
        parse_homework_testcase_archives(io.BytesIO(input_zip), io.BytesIO(output_zip))
    assert "matching filenames" in str(exc.value)

def test_zip_parser_rejects_nested_paths():
    input_zip = _build_zip([("nested/a.txt", b"1")])
    output_zip = _build_zip([("nested/a.txt", b"1")])

    with pytest.raises(HomeworkZipValidationError) as exc:
        parse_homework_testcase_archives(io.BytesIO(input_zip), io.BytesIO(output_zip))
    assert "unsupported member path" in str(exc.value).lower()
