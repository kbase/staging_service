"""
Contains parser functions for use with the file parser framework.
"""

import pandas
import re

# TODO update to C impl when fixed: https://github.com/Marco-Sulla/python-frozendict/issues/26
from frozendict.core import frozendict
from pathlib import Path
from typing import TextIO

from staging_service.import_specifications.file_parser import (
    PRIMITIVE_TYPE,
    ErrorType,
    SpecificationSource,
    Error,
    ParseResult,
    ParseResults,
)

# this version defines the schema of the xsv and Excel files.
# if we need to support a new format, use the version number to detect whether to use
# the current parsing strategy or the new strategy that you will develop.
_VERSION = 1

_DATA_TYPE = "Data type:"
_VERSION_STR = "Version:"
_HEADER_SEP = ";"
_EXPECTED_HEADER = f"{_DATA_TYPE} <data_type>{_HEADER_SEP} {_VERSION_STR} <version>"
_HEADER_REGEX = re.compile(f"{_DATA_TYPE} (\\w+){_HEADER_SEP} {_VERSION_STR} (\\d+)")


class _ParseException(Exception):
    pass


def _parse_header(line: str, spec_source: SpecificationSource, maximum_version: int) -> str:
    # return is data type
    match = _HEADER_REGEX.fullmatch(line)
    if not match:
        raise _ParseException(Error(
            ErrorType.PARSE_FAIL,
            f'Invalid header; got "{line}", expected "{_EXPECTED_HEADER}"',
            spec_source
        ))
    version = int(match[2])
    if version > maximum_version:
        raise _ParseException(Error(
            ErrorType.PARSE_FAIL,
            f"Schema version {version} is larger than maximum processable "
            + f"version {maximum_version}",
            spec_source
        ))
    return match[1]


def _get_datatype(input_: TextIO, spec_source: SpecificationSource, maximum_version: int) -> str:
    try:
        return _parse_header(next(input_).strip(), spec_source, maximum_version)
    except StopIteration:
        raise _ParseException(Error(
            ErrorType.PARSE_FAIL, "Missing data type / version header", spec_source))


def _error(error: Error) -> ParseResults:
    return ParseResults(errors = tuple([error]))


def _strip(putative_str: PRIMITIVE_TYPE) -> PRIMITIVE_TYPE:
    return putative_str.strip() if isinstance(putative_str, str) else putative_str


def _check_for_duplicate_headers(headers: pandas.Index, spec_source: SpecificationSource):
    seen = set()
    for name in headers.get_level_values(0):
        if name in seen:
            raise _ParseException(Error(
                ErrorType.PARSE_FAIL,
                f"Duplicate column name: {name.split('.')[0]}",
                spec_source
            ))
        seen.add(name)


def _validate_xsv_row_count(path: Path, expected_count: int, sep: str):
    with open(path) as input_:
        # since we parsed the first line in the main _parse_xsv method, just discard here
        next(input_)
        for i, line in enumerate(input_):
            # I suppose we could count-- if the last entry is whitespace but f it
            count = 0 if not line.strip() else len(line.split(sep))
            if count != expected_count:
                # could collect errors (first 10?) and throw an exception with a list
                # lets wait and see if that's really needed
                raise _ParseException(Error(
                    ErrorType.PARSE_FAIL,
                    f"Incorrect number of items in line {i + 2}, "
                    + f"expected {expected_count}, got {count}",
                    SpecificationSource(path)
                ))

def _process_dataframe(df: pandas.DataFrame, spec_source: SpecificationSource) -> ParseResult:
    results = []
    recs: list[dict[tuple[str, str], PRIMITIVE_TYPE]] = df.to_dict(orient="records")
    for r in recs:
        results.append(frozendict(
            {headers[0].strip():  # headers is a tuple of the 2 column headers in the xSV
                None if pandas.isna(val) else _strip(val)  # NaN = missing values in pandas
                for headers, val in r.items()}
        ))
    if not results:
        raise _ParseException(Error(
            ErrorType.PARSE_FAIL, "No data found, only headers", spec_source))
    return ParseResult(spec_source, tuple(results))


# TODO README document quoting rules in readme for templates
# TODO README document that non-internal white space is ignored
def _parse_xsv(path: Path, sep: str) -> ParseResults:
    spcsrc = SpecificationSource(path)
    try:
        with open(path) as input_:
            datatype = _get_datatype(input_, spcsrc, _VERSION)
            df = pandas.read_csv(
                input_,
                sep=sep,
                header=[0, 1],
                on_bad_lines="skip",
                skipinitialspace=True,
            )
        # since pandas will autofill rows with missing entries, we check the counts
        # manually
        _validate_xsv_row_count(path, df.columns.shape[0], sep)
        _check_for_duplicate_headers(df.columns, spcsrc)
        return ParseResults(frozendict(
            {datatype: _process_dataframe(df, spcsrc)}
        ))
    except FileNotFoundError:
        return _error(Error(ErrorType.FILE_NOT_FOUND, source_1=spcsrc))
    except _ParseException as e:
        return _error(e.args[0])
    except pandas.errors.EmptyDataError as e:
        if "No columns to parse from file" == str(e):
            return _error(Error(ErrorType.PARSE_FAIL, "Expected 2 column header rows", spcsrc))
        raise e  # bail out, not sure what's wrong, not sure how to test either
    except pandas.errors.ParserError as e:
        if "Passed header=[0,1]" in str(e):
            return _error(Error(ErrorType.PARSE_FAIL, "Expected 2 column header rows", spcsrc))
        raise e  # bail out, not sure what's wrong, not sure how to test either
    except IndexError:
        # ugh. https://github.com/pandas-dev/pandas/issues/43102
        # I really hope I'm not swallowing other pandas bugs here, but not really any way to tell
        return _error(Error(
            ErrorType.PARSE_FAIL, "Header rows have unequal column counts", spcsrc
        ))


def parse_csv(path: Path) -> ParseResults:
    """ Parse the provided CSV file. """
    return _parse_xsv(path, ",")


def parse_tsv(path: Path) -> ParseResults:
    """ Parse the provided TSV file. """
    return _parse_xsv(path, "\t")

