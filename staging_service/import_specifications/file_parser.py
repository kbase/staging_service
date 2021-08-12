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


class SupportedFileType(Enum):
    """
    File types supported by the parser.
    """
    CSV = 1
    TSV = 2
    EXCEL = 3


class ErrorType(Enum):
    """
    The type of an error encountered when trying to parse import specifications.
    """
    FILE_NOT_FOUND = 1
    PARSE_FAIL = 2
    # TODO multiple data type defs error type
    OTHER = 100


@dataclass(frozen=True)
class FileTypeResolution:
    """
    The result of resolving a file type given a file path.

    Only one of type or unsupported_type may be specified.

    type - the resolved file type if the type is one of the supported types.
    unsupported_type - the file type if the type is not a supported type.
    """
    type: SupportedFileType = None
    unsupported_type: str = None

    def __post_init__(self):
        if not (bool(self.type) ^ bool(self.unsupported_type)):  # xnor
            raise ValueError("Exectly one of type or unsupported_type must be supplied")


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
    source - the data source associated with the error, if any

    Each error type has different required arguments:
    {ErrorType.FILE_NOT_FOUND.name}: source
    {ErrorType.PARSE_FAIL}: source and message
    {ErrorType.OTHER}: message. source is optional if the error applies to a source file.

    """
    error: ErrorType
    message: str = None
    source: SpecificationSource = None

    def __post_init__(self):
        if self.error == ErrorType.FILE_NOT_FOUND:
            if not self.source:
                raise ValueError(f'source is required for a {ErrorType.FILE_NOT_FOUND.name} error')
        elif self.error == ErrorType.PARSE_FAIL:
            if not self.source or not self.message:
                pf = ErrorType.PARSE_FAIL.name
                raise ValueError(f'source and message are required for a {pf} error')
        elif self.error == ErrorType.OTHER:
            if not self.message:
                raise ValueError(f'message is required for a {ErrorType.OTHER.name} error')
        else:
            assert 0, "unexpected error type"  # can't test this line


@dataclass(frozen=True)
class ParseResults:
    """
    Contains the results of parsing import specification files.

    results - the parse results. A mapping from the data type, to a tuple containing
        1) the source of the results
        2) the data for the data type as a tuple of dicts.
    errors - the errors encountered while parsing the files, if any.

    Either results or errors must be provided.
    Other than the above check, no other error checking is done by this class, and it is
    expected that the class creator do that error checking. Users should use the
    parse_import_specifications method to create an instance of this class.
    """
    # TODO Result class for 1st tuple
    results: frozendict[str, tuple[SpecificationSource,
        tuple[frozendict[str, PRIMITIVE_TYPE]]]] = None
    errors: tuple[Error] = None

    def __post_init__(self):
        if not (bool(self.results) ^ bool(self.errors)):  # xnor
            raise ValueError("Exectly one of results or errors must be supplied")
        # we assume here that the data is otherwise correctly created.


def parse_import_specifications(
    paths: tuple[Path],
    file_type_resolver: Callable[[Path], FileTypeResolution]
) -> ParseResults:
    """
    Parse a set of import specification files and return the results.

    paths - the file paths to open.
    file_type_resolver - a callable that when given a file path, returns the type of the file.
    """
    results = {}
    errors = []
