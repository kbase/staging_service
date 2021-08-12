"""
Parse import specifications files, either CSV, TSV, or Excel, and return the contents or
error information.
"""

from dataclasses import dataclass
from enum import Enum
# TODO update to C impl when fixed: https://github.com/Marco-Sulla/python-frozendict/issues/26
from frozendict.core import frozendict
from pathlib import Path
from typing import Tuple, Union

# TODO should get mypy working at some point

PRIMITIVE_TYPE = Union[str, int, float, bool, None]


class ErrorType(Enum):
    """
    The type of an error encountered when trying to parse import specifications.
    """
    FILE_NOT_FOUND = 0
    PARSE_FAIL = 1
    OTHER = 2


@dataclass(frozen=True)
class SpecificationSource:
    """
    The source of an import specification.

    file - the file from which the import specification was obtained.
    tab - the spreadsheet file tab from which the import specification was obtained, if any.
    """
    file: Path
    tab: str = None


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
    results: frozendict[str, Tuple[SpecificationSource,
        Tuple[frozendict[str, PRIMITIVE_TYPE]]]] = None
    errors: Tuple[Error] = None

    def __post_init__(self):
        if not (bool(self.results) ^ bool(self.errors)):  # xnor
            raise ValueError("Exectly one of results or errors must be supplied")
        # we assume here that the data is otherwise correctly created.


