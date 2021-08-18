import uuid

from collections.abc import Callable
# TODO update to C impl when fixed: https://github.com/Marco-Sulla/python-frozendict/issues/26
from frozendict.core import frozendict
from pathlib import Path
from pytest import fixture


from staging_service.import_specifications.individual_parsers import (
    parse_csv,
    parse_tsv,
    ErrorType,
    Error,
    SpecificationSource,
    ParseResult,
    ParseResults
)

from tests.test_app import FileUtil

@fixture(scope="module")
def temp_dir() -> Path:
    with FileUtil() as fu:
        childdir = Path(fu.make_dir(str(uuid.uuid4()))).resolve()

        yield childdir

    # FileUtil will auto delete after exiting


def test_xsv_parse_success(temp_dir: Path):
    _xsv_parse_success(temp_dir, ',', parse_csv)
    _xsv_parse_success(temp_dir, '\t', parse_tsv)


def _xsv_parse_success(temp_dir: Path, sep: str, parser: Callable[[Path], ParseResults]):
    s = sep
    input_ = temp_dir / str(uuid.uuid4())
    with open(input_, "w") as test_file:
        test_file.writelines([
            "Data type: some_type; Version: 1\n",
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
            "Data type: other_type; Version: 1\n",
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
            "Data type: other_type; Version: 1\n",
            f"spec1, spec2, spec3, spec4\n",
            f"Spec 1, Spec 2, Spec 3, Spec 4\n",
            f"val1 , val2,    7     , 3.2\n",
        ])
    input_ = Path(str(input_)[-1])

    res = parse_csv(input_)

    assert res == ParseResults(errors=tuple([
        Error(ErrorType.FILE_NOT_FOUND, source_1=SpecificationSource(input_))
    ]))


def _xsv_parse_fail(
    temp_dir: Path, lines: list[str], parser: Callable[[Path], ParseResults], message: str
):
    input_ = temp_dir / str(uuid.uuid4())
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
        + '<data_type>; Version: <version>"')
    _xsv_parse_fail(temp_dir, ["This is the wrong header"], parse_csv, err)


def test_xsv_parse_fail_bad_version(temp_dir: Path):
    err = "Schema version 87 is larger than maximum processable version 1"
    _xsv_parse_fail(temp_dir, ["Data type: foo; Version: 87"], parse_csv, err)

def test_xsv_parse_fail_missing_column_headers(temp_dir: Path):
    err = "Expected 2 column header rows"
    _xsv_parse_fail(temp_dir, ["Data type: foo; Version: 1\n"], parse_csv, err)
    
    lines = ["Data type: foo; Version: 1\n", "head1, head2\n"]
    _xsv_parse_fail(temp_dir, lines, parse_csv, err)


def test_xsv_parse_fail_missing_data(temp_dir: Path):
    err = "No data in file"
    lines = [
        "Data type: foo; Version: 1\n"
        "head1, head2, head3\n",
        "Head 1, Head 2, Head 3\n",
    ]
    _xsv_parse_fail(temp_dir, lines, parse_csv, err)


def test_xsv_parse_fail_unequal_rows(temp_dir: Path):
    err = "Header rows have unequal column counts"
    lines = [
        "Data type: foo; Version: 1\n"
        "head1, head2, head3\n",
        "Head 1, Head 2\n",
    ]
    _xsv_parse_fail(temp_dir, lines, parse_csv, err)

    err = "Incorrect number of items in line 3, expected 2, got 3"
    lines = [
        "Data type: foo; Version: 1\n"
        "head1\thead2\n",
        "Head 1\tHead 2\tHead 3\n",
    ]
    _xsv_parse_fail(temp_dir, lines, parse_tsv, err)

    err = "Incorrect number of items in line 5, expected 3, got 4"
    lines = [
        "Data type: foo; Version: 1\n"
        "head1, head2, head 3\n",
        "Head 1, Head 2, Head 3\n",
        "1, 2, 3\n",
        "1, 2, 3, 4\n",
        "1, 2, 3\n",
    ]
    _xsv_parse_fail(temp_dir, lines, parse_csv, err)

    err = "Incorrect number of items in line 6, expected 3, got 2"
    lines = [
        "Data type: foo; Version: 1\n"
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
        "Data type: foo; Version: 1\n"
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
        "Data type: foo; Version: 1\n"
        "head3, head2, head3\n",
        "Head 1, Head 2, Head 3\n",
    ]
    _xsv_parse_fail(temp_dir, lines, parse_csv, err)