"""
Contains parser functions for use with the file parser framework.
"""

import csv
import magic
import pandas
import re

# TODO update to C impl when fixed: https://github.com/Marco-Sulla/python-frozendict/issues/26
from frozendict.core import frozendict
from pathlib import Path
from typing import TextIO, Optional as O, Union, Any

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
_COLUMN_STR = "Columns:"
_HEADER_SEP = ";"
_EXPECTED_HEADER = (f"{_DATA_TYPE} <data_type>{_HEADER_SEP} "
     + f"{_COLUMN_STR} <column count>{_HEADER_SEP} {_VERSION_STR} <version>")
_HEADER_REGEX = re.compile(f"{_DATA_TYPE} (\\w+){_HEADER_SEP} "
    + f"{_COLUMN_STR} (\\d+){_HEADER_SEP} {_VERSION_STR} (\\d+)")

_MAGIC_TEXT_FILES = {"text/plain", "inode/x-empty"}


class _ParseException(Exception):
    pass


def _parse_header(header: str, spec_source: SpecificationSource, maximum_version: int
) -> tuple[str, int]:
    # return is (data type, column count)
    match = _HEADER_REGEX.fullmatch(header)
    if not match:
        raise _ParseException(Error(
            ErrorType.PARSE_FAIL,
            f'Invalid header; got "{header}", expected "{_EXPECTED_HEADER}"',
            spec_source
        ))
    version = int(match[3])
    if version > maximum_version:
        raise _ParseException(Error(
            ErrorType.PARSE_FAIL,
            f"Schema version {version} is larger than maximum processable "
            + f"version {maximum_version}",
            spec_source
        ))
    return match[1], int(match[2])


def _csv_next(
    input_: Any,  # Any really means a csv reader object
    line_number: int,
    expected_line_count: Union[None, int],  # None = skip columns check
    spec_source: SpecificationSource,
    error: str
) -> list[str]:
    try:
        line = next(input_)
    except StopIteration:
        raise _ParseException(Error(ErrorType.PARSE_FAIL, error, spec_source))
    if expected_line_count and len(line) != expected_line_count:
        raise _ParseException(Error(
            ErrorType.INCORRECT_COLUMN_COUNT,
            f"Incorrect number of items in line {line_number}, "
            + f"expected {expected_line_count}, got {len(line)}",
            spec_source))
    return line


def _error(error: Error) -> ParseResults:
    return ParseResults(errors = tuple([error]))


def _normalize_pandas(val: PRIMITIVE_TYPE) -> PRIMITIVE_TYPE:
    if pandas.isna(val):  # NaN = missing values in pandas
        return None
    if isinstance(val, str):
        val = val.strip()
        return val if val else None
    if isinstance(val, float):
        return int(val) if val.is_integer() else val
    return val


def _normalize_xsv(val: str) -> PRIMITIVE_TYPE:
    # Since csv and tsv rows are all parsed as list[str], regardless of the actual type, we
    # 1) strip any whitespace that might be left around the entries
    # 2) convert to numbers if the string represents a number
    # 3) return None for empty strings, indicating a missing value in the csv
    # If there's a non-numerical string left we return that
    val = val.strip()
    try:
        num = float(val)
        return int(num) if num.is_integer() else num
    except ValueError:
        return val if val else None


def _normalize_headers(
    headers: list[Any], line_number: int, spec_source: SpecificationSource
) -> list[str]:
    seen = set()
    ret = [str(s).strip() if not pandas.isna(s) else None for s in headers]
    for i, name in enumerate(ret, start=1):
        if not name:
            raise _ParseException(Error(
                ErrorType.PARSE_FAIL,
                f"Missing header entry in row {line_number}, position {i}",
                spec_source
            ))

        if name in seen:
            raise _ParseException(Error(
                ErrorType.PARSE_FAIL,
                f"Duplicate header name in row {line_number}: {name}",
                spec_source
            ))
        seen.add(name)
    return ret


def _parse_xsv(path: Path, sep: str) -> ParseResults:
    spcsrc = SpecificationSource(path)
    try:
        if magic.from_file(str(path), mime=True) not in _MAGIC_TEXT_FILES:
            return _error(Error(ErrorType.PARSE_FAIL, "Not a text file", spcsrc))
        with open(path, newline='') as input_:
            rdr = csv.reader(input_, delimiter=sep)  # let parser handle quoting
            dthd = _csv_next(rdr, 1, None, spcsrc, "Missing data type / version header")
            datatype, columns = _parse_header(dthd[0], spcsrc, _VERSION)
            hd1 = _csv_next(rdr, 2, columns, spcsrc, "Missing 2nd header line")
            param_ids = _normalize_headers(hd1, 2, spcsrc)
            _csv_next(rdr, 3, columns, spcsrc, "Missing 3rd header line")
            results = []
            for i, row in enumerate(rdr, start=4):
                if row:  # skip empty rows
                    if len(row) != columns:
                        # could collect errors (first 10?) and throw an exception with a list
                        # lets wait and see if that's really needed
                        raise _ParseException(Error(
                            ErrorType.INCORRECT_COLUMN_COUNT,
                            f"Incorrect number of items in line {i}, "
                            + f"expected {columns}, got {len(row)}",
                            spcsrc))
                    results.append(frozendict(
                        {param_ids[j]: _normalize_xsv(row[j]) for j in range(len(row))}))
        if not results:
            raise _ParseException(Error(
                ErrorType.PARSE_FAIL, "No non-header data in file", spcsrc))
        return ParseResults(frozendict(
            {datatype: ParseResult(spcsrc, tuple(results))}
        ))
    except FileNotFoundError:
        return _error(Error(ErrorType.FILE_NOT_FOUND, source_1=spcsrc))
    except IsADirectoryError:
        return _error(Error(ErrorType.PARSE_FAIL, "The given path is a directory", spcsrc))
    except _ParseException as e:
        return _error(e.args[0])


def parse_csv(path: Path) -> ParseResults:
    """ Parse the provided CSV file. """
    return _parse_xsv(path, ",")


def parse_tsv(path: Path) -> ParseResults:
    """ Parse the provided TSV file. """
    return _parse_xsv(path, "\t")


def _process_excel_row(
    row: tuple[Any], rownum: int, expected_columns: int, spcsrc: SpecificationSource
) -> list[Any]:
    while len(row) > expected_columns:
        if pandas.isna(row[-1]):  # inefficient, but premature optimization...
            row = row[0:-1]
        else:
            raise _ParseException(Error(
                ErrorType.INCORRECT_COLUMN_COUNT,
                f"Incorrect number of items in line {rownum}, "
                + f"expected {expected_columns}, got {len(row)}",
                spcsrc))
    return row
            

def _process_excel_tab(excel: pandas.ExcelFile, spcsrc: SpecificationSource
) -> (O[str], O[ParseResult]):
    df = excel.parse(sheet_name=spcsrc.tab)
    if df.shape[0] < 3:  # might as well not error check headers in sheets with no data
        return (None, None)
    # at this point we know that at least 4 lines are present - expecting the data type header,
    # parameter ID header, display name header, and at least one data row
    header = df.columns.get_level_values(0)[0]
    datatype, columns = _parse_header(header, spcsrc, _VERSION)
    it = df.itertuples(index=False, name=None)
    hd1 = _process_excel_row(next(it), 2, columns, spcsrc)
    param_ids = _normalize_headers(hd1, 2, spcsrc)
    _process_excel_row(next(it), 3, columns, spcsrc)
    results = []
    for i, row in enumerate(it, start=4):
        row = _process_excel_row(row, i, columns, spcsrc)
        if any(map(lambda x: not pandas.isna(x), row)):  # skip empty rows
            results.append(frozendict(
                {param_ids[j]: _normalize_pandas(row[j]) for j in range(len(row))}))
    return datatype, ParseResult(spcsrc, tuple(results))


def parse_excel(path: Path) -> ParseResults:
    """
    Parse the provided Excel file.
    xls and xlsx files are supported.
    """
    spcsrc = SpecificationSource(path)
    errors = []
    try:
        with pandas.ExcelFile(path) as ex:
            results = {}
            datatype_to_tab = {}
            for tab in ex.sheet_names:
                spcsrc_tab = SpecificationSource(path, tab)
                try:
                    datatype, result = _process_excel_tab(ex, spcsrc_tab)
                    if not datatype:
                        continue
                    elif datatype in results:
                        errors.append(Error(
                            ErrorType.MULTIPLE_SPECIFICATIONS_FOR_DATA_TYPE,
                            f"Found datatype {datatype} in multiple tabs",
                            SpecificationSource(path, datatype_to_tab[datatype]),
                            spcsrc_tab,
                        ))
                    else:
                        datatype_to_tab[datatype] = tab
                        results[datatype] = result
                except _ParseException as e:
                    errors.append(e.args[0])
    except FileNotFoundError:
        return _error(Error(ErrorType.FILE_NOT_FOUND, source_1=spcsrc))
    except IsADirectoryError:
        return _error(Error(ErrorType.PARSE_FAIL, "The given path is a directory", spcsrc))
    except ValueError as e:
        if "Excel file format cannot be determined" in str(e):
            return _error(Error(
                ErrorType.PARSE_FAIL, "Not a supported Excel file type", source_1=spcsrc))
        raise e  # bail out, not sure what's wrong, not sure how to test either
    if errors:
        return ParseResults(errors=tuple(errors))
    elif results:
        return ParseResults(frozendict(results))
    else:
        return _error(Error(ErrorType.PARSE_FAIL, "No non-header data in file", spcsrc))
    