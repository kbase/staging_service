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


def test_xsv_parse_success_with_mixed_column(temp_dir: Path):
    """
    This is less a test than a demonstration of current behavior. If the user mixes up rows
    in an import specification such that a string winds up in an integer column, all the values
    are treated as strings. This is a built in pandas behavior so we have to live with it,
    unfortunately - at least without making the templates more heavyweight, which we
    decided not to do for now.
    """
    _xsv_parse_success_with_mixed_column(temp_dir, ',', parse_csv)
    _xsv_parse_success_with_mixed_column(temp_dir, '\t', parse_tsv)


def _xsv_parse_success_with_mixed_column(
    temp_dir: Path, sep: str, parser: Callable[[Path], ParseResults]
):
    s = sep
    input_ = temp_dir / str(uuid.uuid4())
    with open(input_, "w") as test_file:
        test_file.writelines([
            "Data type: other_type; Columns: 4; Version: 1\n",
            f"spec1{s} spec2{s} spec3{s} spec4\n",
            f"Spec 1{s} Spec 2{s} Spec 3{s} Spec 4\n",
            f"val1 {s} val2{s}    7     {s} 3.2\n",
            f"val3 {s} val4{s} 1{s} 8.9\n",
            f"val5 {s} val6{s} int{s} float\n",
        ])

    res = parser(input_)

    assert res == ParseResults(frozendict(
        {"other_type": ParseResult(SpecificationSource(input_),
            tuple([
                frozendict({"spec1": "val1", "spec2": "val2", "spec3": "7", "spec4": "3.2"}),
                frozendict({"spec1": "val3", "spec2": "val4", "spec3": "1", "spec4": "8.9"}),
                frozendict({"spec1": "val5", "spec2": "val6", "spec3": "int", "spec4": "float"}),
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


def _xsv_parse_fail(
    temp_dir: Path,
    lines: list[str],
    parser: Callable[[Path], ParseResults],
    message: str,
    extension: str = "",
):
    input_ = temp_dir / (str(uuid.uuid4()) + extension)
    with open(input_, "w") as test_file:
        test_file.writelines(lines)

    res = parser(input_)
    expected = ParseResults(errors=tuple([Error(
        ErrorType.PARSE_FAIL, message, SpecificationSource(input_)
    )]))
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
    err = "Expected 2 column header rows"
    _xsv_parse_fail(temp_dir, ["Data type: foo; Columns: 3; Version: 1\n"], parse_csv, err)

    lines = ["Data type: foo; Columns: 3; Version: 1\n", "head1, head2\n"]
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
    err = "Header rows have unequal column counts"
    lines = [
        "Data type: foo; Columns: 3; Version: 1\n"
        "head1, head2, head3\n",
        "Head 1, Head 2\n",
    ]
    _xsv_parse_fail(temp_dir, lines, parse_csv, err)

    err = "Incorrect number of items in line 3, expected 2, got 3"
    lines = [
        "Data type: foo; Columns: 2; Version: 1\n"
        "head1\thead2\n",
        "Head 1\tHead 2\tHead 3\n",
    ]
    _xsv_parse_fail(temp_dir, lines, parse_tsv, err)

    err = "Header rows have unequal column counts"
    lines = [
        "Data type: foo; Columns: 2; Version: 1\n"
        "head1, head2, head3\n",
        "Head 1, Head 2\n",
    ]
    _xsv_parse_fail(temp_dir, lines, parse_csv, err)

    err = "Incorrect number of items in line 2, expected 3, got 2"
    lines = [
        "Data type: foo; Columns: 3; Version: 1\n"
        "head1\thead2\n",
        "Head 1\tHead 2\tHead 3\n",
    ]
    _xsv_parse_fail(temp_dir, lines, parse_tsv, err)

    err = "Incorrect number of items in line 5, expected 3, got 4"
    lines = [
        "Data type: foo; Columns: 3; Version: 1\n"
        "head1, head2, head 3\n",
        "Head 1, Head 2, Head 3\n",
        "1, 2, 3\n",
        "1, 2, 3, 4\n",
        "1, 2, 3\n",
    ]
    _xsv_parse_fail(temp_dir, lines, parse_csv, err)

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
    _xsv_parse_fail(temp_dir, lines, parse_tsv, err)

    err = "Incorrect number of items in line 5, expected 3, got 0"
    lines = [
        "Data type: foo; Columns: 3; Version: 1\n"
        "head1, head2, head 3\n",
        "Head 1, Head 2, Head 3\n",
        "1, 2, 3\n",
        "\n",
        "1, 2, 3\n",
    ]
    _xsv_parse_fail(temp_dir, lines, parse_csv, err)


def test_xsv_parse_fail_duplicate_headers(temp_dir: Path):
    err = "Duplicate column name: head3"
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
    Tests files with 3 different tabs with data, including empty cells and whitespace only
    cells, 2 tabs with no data, and one completely empty tab.
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
                frozendict({"h1": "golly gee", "h2": 42, "h3": "super"}),
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


def test_excel_parse_fail_missing_header():
    f = _get_test_file("testmissingheaders.xlsx")
    err = "Missing expected header rows"
    _excel_parse_fail(f, errors=[
        Error(ErrorType.PARSE_FAIL, err, SpecificationSource(f, "badheader1")),
        Error(ErrorType.PARSE_FAIL, err, SpecificationSource(f, "badheader2")),
    ])


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
    l = lambda h: f"Duplicate column name: {h}"
    _excel_parse_fail(f, errors=[
        Error(ErrorType.PARSE_FAIL, l("head1"), SpecificationSource(f, "dt2")),
        Error(ErrorType.PARSE_FAIL, l("head2"), SpecificationSource(f, "dt3")),
    ])


def test_excel_parse_fail_unequal_rows():
    """
    This test differs in a number of ways from the xSV unequal rows test above:
    1) Not having a full row of entries for every column is fine, unlike for xSV files. 
       Spreadsheets provide a clear view of what entries are missing and the user doesn't have to
       worry about off by one errors when filling in separator characters.
    2) Since pandas silently duplicates missing header entries, a missing spec ID header (the
       2nd row) will cause a header duplication error rather than the preferred row count
       error. There doesn't seem to be an easy way around this.
    3) For the above reason, a missing human readable error (row 3) will not cause an error at
       all, since the parser doesn't care about that row other than to skip it.
    """
    f = _get_test_file("testunequalrows.xlsx")
    _excel_parse_fail(f, errors=[
        Error(ErrorType.PARSE_FAIL, "Expected 2 data columns, got 3",
            SpecificationSource(f, "2 cols, 3 human readable")),
        Error(ErrorType.PARSE_FAIL, "Expected 2 data columns, got 3",
            SpecificationSource(f, "2 cols, 3 spec IDs")),
        Error(ErrorType.PARSE_FAIL, "Duplicate column name: head2",
            SpecificationSource(f, "3 cols, 2 spec IDs, header dup error")),
        Error(ErrorType.PARSE_FAIL, "Expected 3 data columns, got 4",
            SpecificationSource(f, "3 cols, 4 data")),
    ])
