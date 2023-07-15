from pathlib import Path

from staging_service.app_error_formatter import format_import_spec_errors
from staging_service.import_specifications.file_parser import (
    Error,
    ErrorType,
    SpecificationSource,
)


def _ss(file: str, tab: str = None) -> SpecificationSource:
    return SpecificationSource(Path(file), tab)


def test_format_import_spec_errors_no_input():
    assert format_import_spec_errors([], {}) == []


def test_format_import_spec_errors_one_error():
    errors = [Error(ErrorType.OTHER, "foobar")]
    assert format_import_spec_errors(errors, {}) == [
        {
            "type": "unexpected_error",
            "message": "foobar",
            "file": None,
        }
    ]


def test_format_import_spec_errors_all_the_errors_no_tabs():
    errors = [
        Error(ErrorType.OTHER, "foobar1", _ss("file1")),
        Error(ErrorType.PARSE_FAIL, "foobar2", _ss("file2")),
        Error(ErrorType.INCORRECT_COLUMN_COUNT, "foobar3", _ss("file3")),
        Error(
            ErrorType.MULTIPLE_SPECIFICATIONS_FOR_DATA_TYPE,
            "foobar4",
            _ss("file4"),
            _ss("file5"),
        ),
        Error(ErrorType.NO_FILES_PROVIDED),
        Error(ErrorType.FILE_NOT_FOUND, source_1=_ss("file6")),
    ]
    paths = {
        Path("file1"): Path("f1"),
        Path("file2"): Path("f2"),
        Path("file3"): Path("f3"),
        Path("file4"): Path("f4"),
        Path("file5"): Path("f5"),
        Path("file6"): Path("f6"),
    }
    assert format_import_spec_errors(errors, paths) == [
        {
            "type": "unexpected_error",
            "message": "foobar1",
            "file": "f1",
        },
        {"type": "cannot_parse_file", "message": "foobar2", "file": "f2", "tab": None},
        {
            "type": "incorrect_column_count",
            "message": "foobar3",
            "file": "f3",
            "tab": None,
        },
        {
            "type": "multiple_specifications_for_data_type",
            "message": "foobar4",
            "file_1": "f4",
            "tab_1": None,
            "file_2": "f5",
            "tab_2": None,
        },
        {"type": "no_files_provided"},
        {
            "type": "cannot_find_file",
            "file": "f6",
        },
    ]


def test_format_import_spec_errors_all_the_errors_with_tabs():
    errors = [
        Error(ErrorType.PARSE_FAIL, "foobar1", _ss("file1", "tab1")),
        Error(ErrorType.INCORRECT_COLUMN_COUNT, "foobar2", _ss("file2", "tab2")),
        Error(
            ErrorType.MULTIPLE_SPECIFICATIONS_FOR_DATA_TYPE,
            "foobar3",
            _ss("file3", "tab3"),
            _ss("file4", "tab4"),
        ),
    ]
    paths = {
        Path("file1"): Path("f1"),
        Path("file2"): Path("f2"),
        Path("file3"): Path("f3"),
        Path("file4"): Path("f4"),
    }
    assert format_import_spec_errors(errors, paths) == [
        {
            "type": "cannot_parse_file",
            "message": "foobar1",
            "file": "f1",
            "tab": "tab1",
        },
        {
            "type": "incorrect_column_count",
            "message": "foobar2",
            "file": "f2",
            "tab": "tab2",
        },
        {
            "type": "multiple_specifications_for_data_type",
            "message": "foobar3",
            "file_1": "f3",
            "tab_1": "tab3",
            "file_2": "f4",
            "tab_2": "tab4",
        },
    ]
