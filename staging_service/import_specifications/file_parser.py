"""
Parse import specifications files, either CSV, TSV, or Excel, and return the contents or
error information.
"""

from dataclasses import dataclass
from enum import Enum
# TODO update to C impl when fixed: https://github.com/Marco-Sulla/python-frozendict/issues/26
from frozendict.core import frozendict
from pathlib import Path
from typing import Dict, Tuple, Union

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
class ParseResults:
    """
    Contains the results of parsing import specification files.

    results - the parse results. A mapping from the data type, to a tuple containing
        1) the source of the results
        2) the data for the data type as a tuple of dicts.
    errortype - the type of any errors encountered while parsing the files.
    errors - error messages on a per data source basis.

    Either results or both errotype and errors must be provided.
    Other than the above check, no other error checking is done by this class, and it is
    expected that the class creator do that error checking. Users should use the
    parse_import_specifications method to create an instance of this class.
    """
    results: frozendict[str, Tuple[SpecificationSource, 
        Tuple[frozendict[str, PRIMITIVE_TYPE]]]] = None
    errortype: ErrorType = None
    errors: frozendict[SpecificationSource, str] = None

    def __post_init__(self):
        if self.results and (self.errortype or self.errors):
            raise ValueError("Cannot include both results and errors")
        if not self.results and (bool(self.errortype) ^ bool(self.errors)):  # xor
            raise ValueError("Both or neither of the errortype and error are required")
        if not self.results and not self.errortype:
            raise ValueError("At least one of results or errors are required")
        # we assume here that the data is otherwise correctly created.


