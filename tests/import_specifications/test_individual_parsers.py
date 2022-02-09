import os
import uuid

from collections.abc import Callable, Generator
# TODO update to C impl when fixed: https://github.com/Marco-Sulla/python-frozendict/issues/26
from frozendict.core import frozendict
from pathlib import Path
from pytest import fixture


from staging_service.import_specifications.individual_parsers import (
    parse_csv,
    parse_tsv,
    parse_excel,
    ErrorType,
    Error,
    SpecificationSource,
    ParseResult,
    ParseResults
)

from tests.test_app import FileUtil

_TEST_DATA_DIR = (Path(__file__).parent / "test_data").resolve()


@fixture(scope="module")
def temp_dir() -> Generator[Path, None, None]:
    with FileUtil() as fu:
        childdir = Path(fu.make_dir(str(uuid.uuid4()))).resolve()

        yield childdir

    # FileUtil will auto delete after exiting

##########################################
# xSV tests
##########################################


def test_xsv_parse_success(temp_dir: Path):
    _xsv_parse_success(temp_dir, ',', parse_csv)
    _xsv_parse_success(temp_dir, '\t', parse_tsv)


def _xsv_parse_success(temp_dir: Path, sep: str, parser: Callable[[Path], ParseResults]):
    s = sep
    input_ = temp_dir / str(uuid.uuid4())
    with open(input_, "w") as test_file:
        test_file.writelines([
            "Data type: some_type; Columns: 4; Version: 1\n",
            f"spec1{s} spec2{s}   spec3   {s} spec4\n",    # test trimming
            f"Spec 1{s} Spec 2{s} Spec 3{s} Spec 4\n",
            f"val1 {s}   val2   {s}    7     {s} 3.2\n",   # test trimming
            f"val3 {s} val4{s} 1{s} 8.9\n",
            f"val5 {s}{s}{s} 42.42\n",                     # test missing values w/o whitespace
            f"val6 {s}      {s}      {s} 3.14\n"           # test missing values w/ whitespace
        ])

    res = parser(input_)

    assert res == ParseResults(frozendict(
        {"some_type": ParseResult(SpecificationSource(input_),
            tuple([
                frozendict({"spec1": "val1", "spec2": "val2", "spec3": 7, "spec4": 3.2}),
                frozendict({"spec1": "val3", "spec2": "val4", "spec3": 1, "spec4": 8.9}),
                frozendict({"spec1": "val5", "spec2": None, "spec3": None, "spec4": 42.42}),
                frozendict({"spec1": "val6", "spec2": None, "spec3": None, "spec4": 3.14}),
            ])
        )}
    ))


def test_xsv_parse_success_with_numeric_headers(temp_dir: Path):
    """
    Not a use case we expect but good to check numeric headers don't cause an unexpected
    error.
    """
    _xsv_parse_success_with_numeric_headers(temp_dir, ',', parse_csv)
    _xsv_parse_success_with_numeric_headers(temp_dir, '\t', parse_tsv)


def _xsv_parse_success_with_numeric_headers(
    temp_dir: Path, sep: str, parser: Callable[[Path], ParseResults]
):
    s = sep
    input_ = temp_dir / str(uuid.uuid4())
    with open(input_, "w") as test_file:
        test_file.writelines([
            "Data type: some_type; Columns: 4; Version: 1\n",
            f"1{s} 2.0{s} 3{s} 4.1\n",    # test trimming
            f"Spec 1{s} Spec 2{s} Spec 3{s} Spec 4\n",
            f"val3 {s} val4{s} 1{s} 8.9\n",
        ])

    res = parser(input_)

    assert res == ParseResults(frozendict(
        {"some_type": ParseResult(SpecificationSource(input_),
            tuple([frozendict({"1": "val3", "2.0": "val4", "3": 1, "4.1": 8.9}),
            ])
        )}
    ))


def _xsv_parse_success_with_internal_and_trailing_empty_lines(temp_dir: Path):
    """
    Test that leaving one or more empty lines in a csv/tsv file does not cause the
    parse to fail. This is easy to do accidentally and so will annoy users.
    """
    _xsv_parse_success_with_internal_and_trailing_empty_lines(temp_dir, ',', parse_csv)
    _xsv_parse_success_with_internal_and_trailing_empty_lines(temp_dir, '\t', parse_tsv)


def _xsv_parse_success_with_internal_and_trailing_empty_lines(
    temp_dir: Path, sep: str, parser: Callable[[Path], ParseResults]
):
    s = sep
    input_ = temp_dir / str(uuid.uuid4())
    with open(input_, "w") as test_file:
        test_file.writelines([
            "Data type: other_type; Columns: 4; Version: 1\n",
            f"spec1{s} spec2{s} spec3{s} spec4\n",
            f"Spec 1{s} Spec 2{s} Spec 3{s} Spec 4\n",
            f"val3 {s} val4{s} 1{s} 8.9\n",
            "\n",
            f"val1 {s} val2{s}    7     {s} 3.2\n",
            "\n",
            "\n",
            "\n",
        ])

    res = parser(input_)

    assert res == ParseResults(frozendict(
        {"other_type": ParseResult(SpecificationSource(input_),
            tuple([
                frozendict({"spec1": "val3", "spec4": "val2", "spec3": 1, "spec4": 8.9}),
                frozendict({"spec1": "val1", "spec2": "val2", "spec3": 7, "spec4": 3.2}),
            ])
        )}
    ))


def test_xsv_parse_fail_no_file(temp_dir: Path):
    input_ = temp_dir / str(uuid.uuid4())
    with open(input_, "w") as test_file:
        test_file.writelines([
            "Data type: other_type; Columns: 4; Version: 1\n",
            "spec1, spec2, spec3, spec4\n",
            "Spec 1, Spec 2, Spec 3, Spec 4\n",
            "val1 , val2,    7     , 3.2\n",
        ])
    input_ = Path(str(input_)[-1])

    res = parse_csv(input_)

    assert res == ParseResults(errors=tuple([
        Error(ErrorType.FILE_NOT_FOUND, source_1=SpecificationSource(input_))
    ]))


def test_xsv_parse_fail_binary_file(temp_dir: Path):
    test_file = _TEST_DATA_DIR / "testtabs3full2nodata1empty.xls"

    res = parse_csv(test_file)

    assert res == ParseResults(errors=tuple([
        Error(ErrorType.PARSE_FAIL, "Not a text file", source_1=SpecificationSource(test_file))
    ]))


def test_xsv_parse_fail_directory(temp_dir: Path):
    test_file = temp_dir / "testdir.tsv"
    os.makedirs(test_file, exist_ok=True)

    res = parse_tsv(test_file)

    assert res == ParseResults(errors=tuple([Error(
        ErrorType.PARSE_FAIL, "The given path is a directory", SpecificationSource(test_file)
    )]))


def _xsv_parse_fail(
    temp_dir: Path,
    lines: list[str],
    parser: Callable[[Path], ParseResults],
    message: str,
    err_type: ErrorType = ErrorType.PARSE_FAIL,
    extension: str = "",
):
    input_ = temp_dir / (str(uuid.uuid4()) + extension)
    with open(input_, "w") as test_file:
        test_file.writelines(lines)

    res = parser(input_)
    expected = ParseResults(errors=tuple([Error(err_type, message, SpecificationSource(input_))]))
    assert res == expected


def test_xsv_parse_fail_empty_file(temp_dir: Path):
    _xsv_parse_fail(temp_dir, [], parse_csv, "Missing data type / version header")


def test_xsv_parse_fail_bad_datatype_header(temp_dir: Path):
    err = ('Invalid header; got "This is the wrong header", expected "Data type: '
        + '<data_type>; Columns: <column count>; Version: <version>"')
    _xsv_parse_fail(temp_dir, ["This is the wrong header"], parse_csv, err)


def test_xsv_parse_fail_bad_version(temp_dir: Path):
    err = "Schema version 87 is larger than maximum processable version 1"
    _xsv_parse_fail(temp_dir, ["Data type: foo; Columns: 22; Version: 87"], parse_csv, err)


def test_xsv_parse_fail_missing_column_headers(temp_dir: Path):
    err = "Missing 2nd header line"
    _xsv_parse_fail(temp_dir, ["Data type: foo; Columns: 3; Version: 1\n"], parse_csv, err)

    err = "Missing 3rd header line"
    lines = ["Data type: foo; Columns: 3; Version: 1\n", "head1, head2, head3\n"]
    _xsv_parse_fail(temp_dir, lines, parse_csv, err)


def test_xsv_parse_fail_missing_column_header_entries(temp_dir: Path):
    err = "Missing header entry in row 2, position 2"
    lines = ["Data type: foo; Columns: 3; Version: 1\n", "head1,  \t , head3\n"]
    _xsv_parse_fail(temp_dir, lines, parse_csv, err)

    lines = ["Data type: foo; Columns: 3; Version: 1\n", "head1,, head3\n"]
    _xsv_parse_fail(temp_dir, lines, parse_csv, err)


def test_xsv_parse_fail_missing_data(temp_dir: Path):
    err = "No non-header data in file"
    lines = [
        "Data type: foo; Columns: 3; Version: 1\n"
        "head1, head2, head3\n",
        "Head 1, Head 2, Head 3\n",
    ]
    _xsv_parse_fail(temp_dir, lines, parse_csv, err)


def test_xsv_parse_fail_unequal_rows(temp_dir: Path):
    err = "Incorrect number of items in line 3, expected 3, got 2"
    lines = [
        "Data type: foo; Columns: 3; Version: 1\n"
        "head1, head2, head3\n",
        "Head 1, Head 2\n",
    ]
    _xsv_parse_fail(temp_dir, lines, parse_csv, err, ErrorType.INCORRECT_COLUMN_COUNT)

    err = "Incorrect number of items in line 3, expected 2, got 3"
    lines = [
        "Data type: foo; Columns: 2; Version: 1\n"
        "head1\thead2\n",
        "Head 1\tHead 2\tHead 3\n",
    ]
    _xsv_parse_fail(temp_dir, lines, parse_tsv, err, ErrorType.INCORRECT_COLUMN_COUNT)

    err = "Incorrect number of items in line 2, expected 2, got 3"
    lines = [
        "Data type: foo; Columns: 2; Version: 1\n"
        "head1, head2, head3\n",
        "Head 1, Head 2\n",
    ]
    _xsv_parse_fail(temp_dir, lines, parse_csv, err, ErrorType.INCORRECT_COLUMN_COUNT)

    err = "Incorrect number of items in line 2, expected 3, got 2"
    lines = [
        "Data type: foo; Columns: 3; Version: 1\n"
        "head1\thead2\n",
        "Head 1\tHead 2\tHead 3\n",
    ]
    _xsv_parse_fail(temp_dir, lines, parse_tsv, err, ErrorType.INCORRECT_COLUMN_COUNT)

    err = "Incorrect number of items in line 5, expected 3, got 4"
    lines = [
        "Data type: foo; Columns: 3; Version: 1\n"
        "head1, head2, head 3\n",
        "Head 1, Head 2, Head 3\n",
        "1, 2, 3\n",
        "1, 2, 3, 4\n",
        "1, 2, 3\n",
    ]
    _xsv_parse_fail(temp_dir, lines, parse_csv, err, ErrorType.INCORRECT_COLUMN_COUNT)

    err = "Incorrect number of items in line 6, expected 3, got 2"
    lines = [
        "Data type: foo; Columns: 3; Version: 1\n"
        "head1\thead2\thead 3\n",
        "Head 1\tHead 2\tHead 3\n",
        "1\t2\t3\n",
        "1\t2\t3\n",
        "1\t2\n",
        "1\t2\t3\n",
    ]
    _xsv_parse_fail(temp_dir, lines, parse_tsv, err, ErrorType.INCORRECT_COLUMN_COUNT)


def test_xsv_parse_fail_duplicate_headers(temp_dir: Path):
    err = "Duplicate header name in row 2: head3"
    lines = [
        "Data type: foo; Columns: 3; Version: 1\n"
        "head3, head2, head3\n",
        "Head 1, Head 2, Head 3\n",
    ]
    _xsv_parse_fail(temp_dir, lines, parse_csv, err)

    # test with duplicate dual headers
    lines = [
        "Data type: foo; Columns: 3; Version: 1\n"
        "head3, head2, head3\n",
        "Head 3, Head 2, Head 3\n",
    ]
    _xsv_parse_fail(temp_dir, lines, parse_csv, err)


##########################################
# Excel tests
#
# Note: for these tests we use actual
#   Excel files saved by LibreOffice
#   rather than using a python writer
##########################################


def _get_test_file(filename: str):
    return _TEST_DATA_DIR / filename


def test_excel_parse_success():
    """
    Tests files with
    * 3 different tabs with data, including
        * numeric headers
        * empty cells
        * empty rows
        * whitespace only cells
    * 2 tabs with no data
    * 1 tab with a single row, which should be ignored
    * 1 tab with two rows, which should be ignored
    * one completely empty tab
    """

    for ext in ["xls", "xlsx"]:
        ex = _get_test_file("testtabs3full2nodata1empty." + ext)

        res = parse_excel(ex)

        assert res == ParseResults(frozendict({
            "type1": ParseResult(SpecificationSource(ex, "tab1"), (
                frozendict({"header1": "foo", "header2": 1, "header3": 6.7}),
                frozendict({"header1": "bar", "header2": 2, "header3": 8.9}),
                frozendict({"header1": "baz", "header2": None, "header3": 3.4}),
                frozendict({"header1": "bat", "header2": 4, "header3": None}),
            )),
            "type2": ParseResult(SpecificationSource(ex, "tab2"), (
                frozendict({"h1": "golly gee", "2": 42, "h3": "super"}),
            )),
            "type3": ParseResult(SpecificationSource(ex, "tab3"), (
                frozendict({"head1": "some data", "head2": 1}),
            )),
        }))


def _excel_parse_fail(
    test_file: str, message: str = None, errors: list[Error] = None, print_res=False
):
    res = parse_excel(test_file)
    if print_res:
        print(res)
        if res.errors:
            for e in res.errors:
                print(e.error)
                print(e.message)
                print(e.source_1)
                print(e.source_2)

    if errors:
        assert res == ParseResults(errors=tuple(errors))
    else:
        assert res == ParseResults(errors=tuple([
            Error(ErrorType.PARSE_FAIL, message, source_1=SpecificationSource(test_file))
        ]))


def test_excel_parse_fail_no_file():
    f = _get_test_file("testtabs3full2nodata1empty0.xls")
    _excel_parse_fail(f, errors=[
        Error(ErrorType.FILE_NOT_FOUND, source_1=SpecificationSource(f))
    ])


def test_excel_parse_fail_directory(temp_dir):
    for d in ["testdir.xls", "testdir.xlsx"]:
        f = temp_dir / d
        os.makedirs(f, exist_ok=True)
        err = "The given path is a directory"
        _excel_parse_fail(f, errors=[Error(ErrorType.PARSE_FAIL, err, SpecificationSource(f))])


def test_excel_parse_fail_empty_file(temp_dir: Path):
    _xsv_parse_fail(temp_dir, [], parse_excel, "Not a supported Excel file type", extension=".xls")


def test_excel_parse_fail_non_excel_file(temp_dir: Path):
    lines = [
        "Data type: foo; Version: 1\n"
        "head1, head2, head 3\n",
        "Head 1, Head 2, Head 3\n",
        "1, 2, 3\n",
    ]
    _xsv_parse_fail(
        temp_dir, lines, parse_excel, "Not a supported Excel file type", extension=".xlsx")


def test_excel_parse_1emptytab():
    _excel_parse_fail(_get_test_file("testtabs1empty.xls"), "No non-header data in file")


def test_excel_parse_fail_bad_datatype_header():
    f = _get_test_file("testbadinitialheader.xls")
    err1 = ('Invalid header; got "This header is wack, yo", expected "Data type: '
        + '<data_type>; Columns: <column count>; Version: <version>"')
    err2 = "Schema version 2 is larger than maximum processable version 1"
    _excel_parse_fail(f, errors=[
        Error(ErrorType.PARSE_FAIL, err1, SpecificationSource(f, "badheader1")),
        Error(ErrorType.PARSE_FAIL, err2, SpecificationSource(f, "badheader2")),
    ])


def test_excel_parse_fail_headers_only():
    f = _get_test_file("testheadersonly.xlsx")
    _excel_parse_fail(f, "No non-header data in file")


def test_excel_parse_fail_colliding_datatypes():
    f = _get_test_file("testdatatypecollisions.xls")
    l = lambda t: f"Found datatype {t} in multiple tabs"
    err = ErrorType.MULTIPLE_SPECIFICATIONS_FOR_DATA_TYPE
    _excel_parse_fail(f, errors=[
        Error(err, l("type2"), SpecificationSource(f, "dt2"), SpecificationSource(f, "dt2_2")),
        Error(err, l("type3"), SpecificationSource(f, "dt3"), SpecificationSource(f, "dt3_2")),
        Error(err, l("type2"), SpecificationSource(f, "dt2"), SpecificationSource(f, "dt2_3")),
    ])


def test_excel_parse_fail_duplicate_headers():
    f = _get_test_file("testduplicateheaders.xlsx")
    l = lambda h: f"Duplicate header name in row 2: {h}"
    _excel_parse_fail(f, errors=[
        Error(ErrorType.PARSE_FAIL, l("head1"), SpecificationSource(f, "dt2")),
        Error(ErrorType.PARSE_FAIL, l("head2"), SpecificationSource(f, "dt3")),
    ])


def test_excel_parse_fail_missing_header_item():
    f = _get_test_file("testmissingheaderitem.xlsx")
    err1 = "Missing header entry in row 2, position 3"
    err2 = "Missing header entry in row 2, position 2"
    _excel_parse_fail(f, errors=[
        Error(ErrorType.PARSE_FAIL, err1, SpecificationSource(f, "missing header item error")),
        Error(ErrorType.PARSE_FAIL, err2, SpecificationSource(f, "whitespace header item")),
    ])

def test_excel_parse_fail_unequal_rows():
    """
    This test differs from the xSV unequal rows test above in that not having a full row of
    entries for every column is fine, unlike for xSV files.
    Spreadsheets provide a clear view of what entries are missing and the user doesn't have to
    worry about off by one errors when filling in separator characters.
    """
    f = _get_test_file("testunequalrows.xlsx")
    _excel_parse_fail(f, errors=[
        Error(
            ErrorType.INCORRECT_COLUMN_COUNT,
            "Incorrect number of items in line 3, expected 2, got 3",
            SpecificationSource(f, "2 cols, 3 human readable")
        ),
        Error(
            ErrorType.INCORRECT_COLUMN_COUNT,
            "Incorrect number of items in line 2, expected 2, got 3",
            SpecificationSource(f, "2 cols, 3 spec IDs")
        ),
        Error(
            ErrorType.INCORRECT_COLUMN_COUNT,
            "Incorrect number of items in line 5, expected 3, got 4",
            SpecificationSource(f, "3 cols, 4 data")
        ),
    ])
