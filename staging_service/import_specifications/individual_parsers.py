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


def _required_next(
    input_: Union[TextIO, Any],  # Any really means a csv reader object
    spec_source: SpecificationSource,
    error: str
) -> Union[str, list[str]]:
    # returns a string for a TextIO input or a list for a Reader input
    try:
        return next(input_)
    except StopIteration:
        raise _ParseException(Error(ErrorType.PARSE_FAIL, error, spec_source))

def _csv_next(
    input_: Union[TextIO, Any],  # Any really means a csv reader object
    line_number: int,
    expected_line_count: int,
    spec_source: SpecificationSource,
    error: str
) -> list[str]:
    line = _required_next(input_, spec_source, error)
    if len(line) != expected_line_count:
        raise _ParseException(Error(
            ErrorType.INCORRECT_COLUMN_COUNT,
            f"Incorrect number of items in line {line_number}, "
            + f"expected {expected_line_count}, got {len(line)}",
            spec_source))
    return line


def _get_datatype(input_: TextIO, spec_source: SpecificationSource, maximum_version: int
) -> tuple[str, int]:
    # return is (data type, column count)
    return _parse_header(
        _required_next(input_, spec_source, "Missing data type / version header").strip(),
        spec_source,
        maximum_version)


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


def _normalize(val: str) -> PRIMITIVE_TYPE:
    val = val.strip()
    try:
        num = float(val)
        return int(num) if num.is_integer() else num
    except ValueError:
        return val if val else None


def _check_for_duplicate_headers(
    headers: pandas.Index, spec_source: SpecificationSource, header_index=0
):
    seen = set()
    for name in headers.get_level_values(header_index):
        if name in seen:
            raise _ParseException(Error(
                ErrorType.PARSE_FAIL,
                f"Duplicate column name: {name.split('.')[0]}",
                spec_source
            ))
        seen.add(name)


def _normalize_headers(
    headers: list[str], line_number: int, spec_source: SpecificationSource
) -> list[str]:
    seen = set()
    ret = [s.strip() for s in headers]
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


def _process_dataframe(df: pandas.DataFrame, spec_source: SpecificationSource, header_index=0
) -> ParseResult:
    results = []
    recs: list[dict[tuple[str, ...], PRIMITIVE_TYPE]] = df.to_dict(orient="records")
    for r in recs:
        results.append(frozendict(
            # headers is a tuple of the column headers
            {headers[header_index].strip(): _normalize_pandas(val) for headers, val in r.items()}
        ))
    if not results:
        raise _ParseException(Error(
            ErrorType.PARSE_FAIL, "No non-header data in file", spec_source))
    return ParseResult(spec_source, tuple(results))


def _parse_xsv(path: Path, sep: str) -> ParseResults:
    spcsrc = SpecificationSource(path)
    try:
        if magic.from_file(str(path), mime=True) not in _MAGIC_TEXT_FILES:
            return _error(Error(ErrorType.PARSE_FAIL, "Not a text file", spcsrc))
        with open(path, newline='') as input_:
            datatype, columns = _get_datatype(input_, spcsrc, _VERSION)
            rdr = csv.reader(input_, delimiter=sep)  # let parser handle quoting
            hd1 = _csv_next(rdr, 2, columns, spcsrc, "Missing 2nd header line")
            param_ids = _normalize_headers(hd1, 2, spcsrc)
            _csv_next(rdr, 3, columns, spcsrc, "Missing 3rd header line")
            results = []
            for i, row in enumerate(rdr, start=4):
                if row and len(row) != columns:  # skip empty rows
                    # could collect errors (first 10?) and throw an exception with a list
                    # lets wait and see if that's really needed
                    raise _ParseException(Error(
                        ErrorType.INCORRECT_COLUMN_COUNT,
                        f"Incorrect number of items in line {i}, "
                        + f"expected {columns}, got {len(row)}",
                        spcsrc))
                results.append(frozendict(
                    {param_ids[j]: _normalize(row[j]) for j in range(len(row))}))
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


def _load_excel_tab_to_dataframe(excel: pandas.ExcelFile, spcsrc: SpecificationSource
) -> pandas.DataFrame:
    try:
        return excel.parse(sheet_name=spcsrc.tab, header=[0, 1, 2])
    except IndexError:
        # ugh. https://github.com/pandas-dev/pandas/issues/43143
        # I really hope I'm not swallowing other pandas bugs here, but not really
        # any way to tell
        # Not fixed as of pandas 1.4.0
        raise _ParseException(Error(
            ErrorType.PARSE_FAIL, "Missing expected header rows", spcsrc
        ))


def _process_excel_tab(excel: pandas.ExcelFile, spcsrc: SpecificationSource
) -> (O[str], O[ParseResult]):
    df = _load_excel_tab_to_dataframe(excel, spcsrc)
    if df.empty:  # might as well not error check headers in sheets with no data
        return (None, None)  # next line will throw an error for a completely empty sheet
    # at this point we know that the 3 headers are present
    header = df.columns.get_level_values(0)[0]
    datatype, columns = _parse_header(header, spcsrc, _VERSION)
    # Could run through the entire sheet looking for non-NaN values to find offending rows
    # Seems like a lot of complexity. If this becomes a problem reconsider
    # Can't catch some header errors anyway, since pandas duplicates them silently
    if df.columns.shape[0] != columns:
        raise _ParseException(Error(
            ErrorType.INCORRECT_COLUMN_COUNT,
            f"Expected {columns} data columns, got {df.columns.shape[0]}",
            spcsrc,
        ))
    _check_for_duplicate_headers(df.columns, spcsrc, header_index=1)
    return datatype, _process_dataframe(df, spcsrc, header_index=1)


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
    