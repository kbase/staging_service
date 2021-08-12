"""
Parse import specifications files, either CSV, TSV, or Excel, and return the contents or
error information.
"""

from dataclasses import dataclass
from enum import Enum
# TODO update to C impl when fixed: https://github.com/Marco-Sulla/python-frozendict/issues/26
from frozendict.core import frozendict
from pathlib import Path
from typing import Union, Callable

# TODO should get mypy working at some point

PRIMITIVE_TYPE = Union[str, int, float, bool, None]


class ErrorType(Enum):
    """
    The type of an error encountered when trying to parse import specifications.
    """
    FILE_NOT_FOUND = 1
    PARSE_FAIL = 2
    MULTIPLE_SPECIFICATIONS_FOR_DATA_TYPE = 3
    OTHER = 100


@dataclass(frozen=True)
class SpecificationSource:
    """
    The source of an import specification.

    file - the file from which the import specification was obtained.
    tab - the name of the spreadsheet file tab from which the import specification was obtained,
        if any.
    """
    file: Path
    tab: str = None

    def __post_init__(self):
        if not self.file:
            raise ValueError("file is required")


@dataclass(frozen=True)
class Error:
    f"""
    An error found while attempting to parse files.

    error - the type of the error.
    message - the error message, if any
    source_1 - the first data source associated with the error, if any
    source_2 - the second data source associated with the error, if any

    Each error type has different required arguments:
    {ErrorType.FILE_NOT_FOUND.name}: source_1
    {ErrorType.PARSE_FAIL}: message and source_1
    {ErrorType.MULTIPLE_SPECIFICATIONS_FOR_DATA_TYPE}: message, source_1, and source_2
    {ErrorType.OTHER}: message. source_* is optional if the error applies to one or more
        source files.

    """
    error: ErrorType
    message: str = None
    source_1: SpecificationSource = None
    source_2: SpecificationSource = None

    def __post_init__(self):
        if not self.error:
            raise ValueError("error is required")
        if self.error == ErrorType.FILE_NOT_FOUND:
            if not self.source_1:
                raise ValueError(
                    f"source_1 is required for a {ErrorType.FILE_NOT_FOUND.name} error")
        elif self.error == ErrorType.PARSE_FAIL:
            if not self.source_1 or not self.message:
                pf = ErrorType.PARSE_FAIL.name
                raise ValueError(f'message and source_1 are required for a {pf} error')
        elif self.error == ErrorType.MULTIPLE_SPECIFICATIONS_FOR_DATA_TYPE:
            if not self.message or not self.source_1 or not self.source_2:
                ms = ErrorType.MULTIPLE_SPECIFICATIONS_FOR_DATA_TYPE.name
                raise ValueError(f"message, source_1, and source_2 are required for a {ms} error")
        elif self.error == ErrorType.OTHER:
            if not self.message:
                raise ValueError(f'message is required for a {ErrorType.OTHER.name} error')
        else:
            assert 0, "unexpected error type"  # can't test this line


@dataclass(frozen=True)
class ParseResult:
    """
    Contains the result of parsing one import specification, usually a single xSV file or a
    spreadsheet tab.

    source - the source of the import specification
    result - the result of parsing the specification

    Both arguments are required.
    Other than the above check, no other error checking is done by this class, and it is
    expected that the class creator do that error checking. Users should use the
    parse_import_specifications method to create instances of this class.
    """
    source: SpecificationSource
    result: tuple[frozendict[str, PRIMITIVE_TYPE]]

    def __post_init__(self):
        if not self.source:
            raise ValueError("source is required")
        if not self.result:
            raise ValueError("result is required")
        # we assume here that the data is otherwise correctly created.


@dataclass(frozen=True)
class ParseResults:
    """
    Contains the results of parsing import specification files.

    results - the parse results. A mapping from the data type to a result containing
        1) the source of the results
        2) the data for the data type
    errors - the errors encountered while parsing the files, if any.

    Either results or errors must be provided.
    Other than the above check, no other error checking is done by this class, and it is
    expected that the class creator do that error checking. Users should use the
    parse_import_specifications method to create an instance of this class.
    """
    results: frozendict[str, ParseResult] = None
    errors: tuple[Error] = None

    def __post_init__(self):
        if not (bool(self.results) ^ bool(self.errors)):  # xnor
            raise ValueError("Exectly one of results or errors must be supplied")
        # we assume here that the data is otherwise correctly created.


@dataclass(frozen=True)
class FileTypeResolution:
    """
    The result of resolving a file type given a file path.

    Only one of parser or unsupported_type may be specified.

    parser - a parser for the file
    unsupported_type - the file type if the type is not a supported type.
    """
    parser: Callable[[Path], ParseResults] = None
    unsupported_type: str = None

    def __post_init__(self):
        if not (bool(self.parser) ^ bool(self.unsupported_type)):  # xnor
            raise ValueError("Exectly one of parser or unsupported_type must be supplied")


def parse_import_specifications(
    paths: tuple[Path],
    file_type_resolver: Callable[[Path], FileTypeResolution]
) -> ParseResults:
    """
    Parse a set of import specification files and return the results.

    paths - the file paths to open.
    file_type_resolver - a callable that when given a file path, returns the type of the file or
        a parser for the file.
    """
    results = {}
    errors = []
