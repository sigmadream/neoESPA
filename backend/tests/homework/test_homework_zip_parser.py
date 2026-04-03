import io
import pytest
import zipfile
from app.domains.homework.zip_parser import parse_homework_testcase_archives, HomeworkZipValidationError

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
