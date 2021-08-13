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
    NO_FILES_PROVIDED = 4
    # TODO illegal file
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


_ERR_MESSAGE = 'message'
_ERR_SOURCE_1 = 'source_1'
_ERR_SOURCE_2 = 'source_2'

_ERRTYPE_TO_REQ_ARGS = {
    ErrorType.FILE_NOT_FOUND: (_ERR_SOURCE_1,),
    ErrorType.PARSE_FAIL: (_ERR_MESSAGE, _ERR_SOURCE_1),
    ErrorType.MULTIPLE_SPECIFICATIONS_FOR_DATA_TYPE: (_ERR_MESSAGE, _ERR_SOURCE_1, _ERR_SOURCE_2),
    ErrorType.NO_FILES_PROVIDED: tuple(),
    ErrorType.OTHER: (_ERR_MESSAGE,),
}

@dataclass(frozen=True)
class Error:
    f"""
    An error found while attempting to parse files.

    error - the type of the error.
    {_ERR_MESSAGE} - the error message, if any
    {_ERR_SOURCE_1} - the first data source associated with the error, if any
    {_ERR_SOURCE_2} - the second data source associated with the error, if any

    Each error type has different required arguments:
    {ErrorType.FILE_NOT_FOUND.name}: {_ERR_SOURCE_1}
    {ErrorType.PARSE_FAIL}: {_ERR_MESSAGE} and {_ERR_SOURCE_1}
    {ErrorType.MULTIPLE_SPECIFICATIONS_FOR_DATA_TYPE}: {_ERR_MESSAGE}, {_ERR_SOURCE_1}, and
        {_ERR_SOURCE_2}
    {ErrorType.NO_FILES_PROVIDED}: none
    {ErrorType.OTHER}: {_ERR_MESSAGE}. source arguments are optional and may be included if
        the error applies to one or more source files.

    """
    error: ErrorType
    message: str = None
    source_1: SpecificationSource = None
    source_2: SpecificationSource = None

    def __post_init__(self):
        if not self.error:
            raise ValueError("error is required")
        if self.error not in _ERRTYPE_TO_REQ_ARGS:
            # can't test this line in a meaningful way
            assert 0, f"unexpected error type: {self.error}"
        attrs = _ERRTYPE_TO_REQ_ARGS[self.error]
        for attr in attrs:
            if not getattr(self, attr):
                # grammar sucks but this is not expected to be seen by end users so meh
                raise ValueError(f"{', '.join(attrs)} is required for a {self.error.name} error")


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
