"""
This module formats error classes into primitive types and containers.
"""

from pathlib import Path

from .import_specifications.file_parser import ErrorType, Error

# Types for the lambda parameters are all strings
# We don't add hints in to avoid repeating them over and over
_IMPORT_SPEC_ERROR_FORMATTERS = {
    ErrorType.OTHER: lambda msg, file1, tab1, file2, tab2: {
        "type": "unexpected_error",
        "message": msg,
        "file": file1,
    },
    ErrorType.FILE_NOT_FOUND: lambda msg, file1, tab1, file2, tab2: {
        "type": "cannot_find_file",
        "file": file1,
    },
    ErrorType.NO_FILES_PROVIDED: lambda msg, file1, tab1, file2, tab2: {
        "type": "no_files_provided",
    },
    ErrorType.PARSE_FAIL: lambda msg, file1, tab1, file2, tab2: {
        "type": "cannot_parse_file",
        "message": msg,
        "file": file1,
        "tab": tab1
    },
    ErrorType.INCORRECT_COLUMN_COUNT: lambda msg, file1, tab1, file2, tab2: {
        "type": "incorrect_column_count",
        "message": msg,
        "file": file1,
        "tab": tab1
    },
    ErrorType.MULTIPLE_SPECIFICATIONS_FOR_DATA_TYPE: lambda msg, file1, tab1, file2, tab2: {
        "type": "multiple_specifications_for_data_type",
        "message": msg,
        "file_1": file1,
        "tab_1": tab1,
        "file_2": file2,
        "tab_2": tab2,
    },
}

def format_import_spec_errors(errors: list[Error], path_translations: dict[Path, Path]
) -> list[dict[str, str]]:
    """
    Formats a list of bulk import specification errors into a list of str->str dicts.

    errors: The errors to format
    path_translations: A translation mapping to apply to paths in the errors. Each path in the
        errors must have a mapping in this list. Typically used to translate an internal path
        to a path that is interpretable by a user.
    """
    errs = []
    for e in errors:
        file1 = None
        tab1 = None
        file2 = None
        tab2 = None
        if e.source_1:
            file1 = str(path_translations[e.source_1.file])
            tab1 = e.source_1.tab
        if e.source_2:
            file2 = str(path_translations[e.source_2.file])
            tab2 = e.source_2.tab
        errs.append(_IMPORT_SPEC_ERROR_FORMATTERS[e.error](e.message, file1, tab1, file2, tab2))
    return errs

