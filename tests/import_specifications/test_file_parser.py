# not much point in testing data classes unless there's custom logic in them

from collections.abc import Callable
from pathlib import Path
from typing import Optional
from unittest.mock import Mock, call

from frozendict import frozendict
from pytest import raises

from staging_service.import_specifications.file_parser import (
    PRIMITIVE_TYPE,
    Error,
    ErrorType,
    FileTypeResolution,
    ParseResult,
    ParseResults,
    SpecificationSource,
    parse_import_specifications,
)
from tests.test_helpers import assert_exception_correct

TEST_EXCEL_FILE = "myfile.xlsx"

# This file does not exist, it is used for a mock, appears in many locations.
TEST_MOCK_CSV_FILE_NAME = "somefile.csv"

# some test functions include "SpecificationSource" in the name, which violates
# snake_case rules, but is meaningful in this context.
# pylint: disable=C0103
# pylint: disable=C0116


def specification_source(path: str, tab: Optional[str] = None):
    return SpecificationSource(Path(path), tab)


def test_specification_source_init_success():
    # minimal
    ss = SpecificationSource(Path("foo"))

    assert ss.file == Path("foo")
    assert ss.tab is None

    # all
    ss = SpecificationSource(Path("bar"), "tabbytab")

    assert ss.file == Path("bar")
    assert ss.tab == "tabbytab"


def test_specification_source_init_fail():
    # could inline this, but might as well follow the same pattern as all the other tests
    assert_specification_source_init_fail(None, ValueError("file is required"))


def assert_specification_source_init_fail(file: Optional[str], expected: Exception):
    with raises(Exception) as got:
        SpecificationSource(file)
    assert_exception_correct(got.value, expected)


def test_file_type_resolution_init_w_parser_success():
    def parser(_: str):
        return ParseResults(errors=(Error(ErrorType.OTHER, "foo"),))

    ftr = FileTypeResolution(parser)

    assert ftr.parser is parser  # Here only identity equality makes sense
    assert ftr.unsupported_type is None


def test_file_type_resolution_init_w_unsupported_type_success():
    ftr = FileTypeResolution(unsupported_type="sys")

    assert ftr.parser is None
    assert ftr.unsupported_type == "sys"


def test_file_type_resolution_init_fail():
    err = "Exactly one of parser or unsupported_type must be supplied"
    pr = ParseResults(errors=(Error(ErrorType.OTHER, "foo"),))
    assert_file_type_resolution_init_fail(None, None, ValueError(err))
    assert_file_type_resolution_init_fail(lambda path: pr, "mp-2", ValueError(err))


def assert_file_type_resolution_init_fail(
    parser: Optional[Callable[[Path], ParseResults]],
    unexpected_type: Optional[str],
    expected: Exception,
):
    with raises(Exception) as got:
        FileTypeResolution(parser, unexpected_type)
    assert_exception_correct(got.value, expected)


def test_error_init_w_file_not_found_success():
    # minimal
    e = Error(ErrorType.FILE_NOT_FOUND, source_1=specification_source("foo"))

    assert e.error == ErrorType.FILE_NOT_FOUND
    assert e.message is None
    assert e.source_1 == specification_source("foo")
    assert e.source_2 is None

    # all
    e = Error(
        ErrorType.FILE_NOT_FOUND, message="bar", source_1=specification_source("foo")
    )

    assert e.error == ErrorType.FILE_NOT_FOUND
    assert e.message == "bar"
    assert e.source_1 == specification_source("foo")
    assert e.source_2 is None


def test_error_init_w_parse_fail_success():
    e = Error(
        ErrorType.PARSE_FAIL, message="foo", source_1=specification_source("foo2")
    )

    assert e.error == ErrorType.PARSE_FAIL
    assert e.message == "foo"
    assert e.source_1 == specification_source("foo2")
    assert e.source_2 is None


def test_error_init_w_incorrect_column_count_success():
    e = Error(
        ErrorType.INCORRECT_COLUMN_COUNT,
        message="42",
        source_1=specification_source("some_other_file"),
    )

    assert e.error == ErrorType.INCORRECT_COLUMN_COUNT
    assert e.message == "42"
    assert e.source_1 == specification_source("some_other_file")
    assert e.source_2 is None


def test_error_init_w_multiple_specifications_for_data_type_success():
    e = Error(
        ErrorType.MULTIPLE_SPECIFICATIONS_FOR_DATA_TYPE,
        "foo",
        specification_source("foo2"),
        specification_source("yay"),
    )

    assert e.error == ErrorType.MULTIPLE_SPECIFICATIONS_FOR_DATA_TYPE
    assert e.message == "foo"
    assert e.source_1 == specification_source("foo2")
    assert e.source_2 == specification_source("yay")


def test_error_init_w_no_files_provided_success():
    e = Error(ErrorType.NO_FILES_PROVIDED)

    assert e.error == ErrorType.NO_FILES_PROVIDED
    assert e.message is None
    assert e.source_1 is None
    assert e.source_2 is None


def test_error_init_w_other_success():
    # minimal
    e = Error(ErrorType.OTHER, message="foo")

    assert e.error == ErrorType.OTHER
    assert e.message == "foo"
    assert e.source_1 is None
    assert e.source_2 is None

    # all
    e = Error(ErrorType.OTHER, message="foo", source_1=specification_source("wooo"))

    assert e.error == ErrorType.OTHER
    assert e.message == "foo"
    assert e.source_1 == specification_source("wooo")
    assert e.source_2 is None


def test_error_init_fail():
    # arguments are error type, message string, 1st source, 2nd source, exception
    error_init_fail(None, None, None, None, ValueError("error is required"))
    error_init_fail(
        ErrorType.FILE_NOT_FOUND,
        None,
        None,
        None,
        ValueError("source_1 is required for a FILE_NOT_FOUND error"),
    )
    err = "message, source_1 is required for a PARSE_FAIL error"
    error_init_fail(
        ErrorType.PARSE_FAIL, None, specification_source("wooo"), None, ValueError(err)
    )
    error_init_fail(ErrorType.PARSE_FAIL, "msg", None, None, ValueError(err))
    err = "message, source_1 is required for a INCORRECT_COLUMN_COUNT error"
    error_init_fail(
        ErrorType.INCORRECT_COLUMN_COUNT,
        None,
        specification_source("whee"),
        None,
        ValueError(err),
    )
    error_init_fail(
        ErrorType.INCORRECT_COLUMN_COUNT, "msg", None, None, ValueError(err)
    )
    ms = ErrorType.MULTIPLE_SPECIFICATIONS_FOR_DATA_TYPE
    err = (
        "message, source_1, source_2 is required for a "
        + "MULTIPLE_SPECIFICATIONS_FOR_DATA_TYPE error"
    )
    error_init_fail(ms, None, None, None, ValueError(err))
    error_init_fail(
        ms,
        None,
        specification_source("foo"),
        specification_source("bar"),
        ValueError(err),
    )
    error_init_fail(ms, "msg", None, specification_source("bar"), ValueError(err))
    error_init_fail(ms, "msg", specification_source("foo"), None, ValueError(err))
    error_init_fail(
        ErrorType.OTHER,
        None,
        None,
        None,
        ValueError("message is required for a OTHER error"),
    )


def error_init_fail(
    errortype: Optional[ErrorType],
    message: Optional[str],
    source_1: Optional[SpecificationSource],
    source_2: Optional[SpecificationSource],
    expected: Exception,
):
    with raises(Exception) as got:
        Error(errortype, message, source_1, source_2)
    assert_exception_correct(got.value, expected)


def test_parse_result_init_success():
    pr = ParseResult(specification_source("bar"), (frozendict({"foo": "bar"}),))

    assert pr.source == specification_source("bar")
    assert pr.result == (frozendict({"foo": "bar"}),)


def test_parse_result_init_fail():
    assert_parse_result_init_fail(None, None, ValueError("source is required"))
    assert_parse_result_init_fail(
        None, (frozendict({"foo": "bar"}),), ValueError("source is required")
    )
    assert_parse_result_init_fail(
        specification_source("foo"), None, ValueError("result is required")
    )


def assert_parse_result_init_fail(
    source: Optional[SpecificationSource],
    result: Optional[tuple[frozendict[str, PRIMITIVE_TYPE], ...]],
    expected: Exception,
):
    with raises(Exception) as got:
        ParseResult(source, result)
    assert_exception_correct(got.value, expected)


PR_RESULTS = frozendict(
    {
        "data_type": ParseResult(
            specification_source("some_file", "tab"),
            (frozendict({"fasta_file": "foo.fa", "do_thing": 1}),),  # make a tuple!
        )
    }
)

PR_ERROR = (
    Error(ErrorType.OTHER, message="foo"),
    Error(
        ErrorType.PARSE_FAIL,
        message="bar",
        source_1=specification_source("some_file", "tab3"),
    ),
)


def test_parse_results_init_w_results_success():
    results_copy = frozendict(PR_RESULTS)  # prevent identity equality

    pr = ParseResults(PR_RESULTS)
    assert pr.results == results_copy
    assert pr.errors is None

    assert pr == ParseResults(results_copy)


def test_parse_results_init_w_error_success():
    errors_copy = tuple(PR_ERROR)  # prevent identity equality

    pr = ParseResults(errors=PR_ERROR)
    assert pr.results is None
    assert pr.errors == errors_copy

    assert pr == ParseResults(errors=errors_copy)


def test_parse_results_init_fail():
    err = "Exactly one of results or errors must be supplied"
    assert_parse_results_init_fail(None, None, ValueError(err))
    assert_parse_results_init_fail(PR_RESULTS, PR_ERROR, ValueError(err))


def assert_parse_results_init_fail(
    results: Optional[frozendict[str, ParseResult]],
    errors: Optional[tuple[Error, ...]],
    expected: ValueError,
):
    with raises(Exception) as got:
        ParseResults(results, errors)
    assert_exception_correct(got.value, expected)


def _ftr(
    parser: Callable[[Path], ParseResults] = None, notype: str = None
) -> FileTypeResolution:
    return FileTypeResolution(parser, notype)


def _get_mocks(count: int) -> tuple[Mock, ...]:
    return (Mock() for _ in range(count))


def test_parse_import_specifications_success():
    resolver, logger, parser1, parser2 = _get_mocks(4)

    resolver.side_effect = [_ftr(parser1), _ftr(parser2)]

    parser1.return_value = ParseResults(
        frozendict(
            {
                "type1": ParseResult(
                    specification_source(TEST_EXCEL_FILE, "tab1"),
                    (frozendict({"foo": "bar"}), frozendict({"baz": "bat"})),
                ),
                "type2": ParseResult(
                    specification_source(TEST_EXCEL_FILE, "tab2"),
                    (frozendict({"whee": "whoo"}),),  # tuple!
                ),
            }
        )
    )

    parser2.return_value = ParseResults(
        frozendict(
            {
                "type_other": ParseResult(
                    specification_source(TEST_MOCK_CSV_FILE_NAME),
                    (frozendict({"foo": "bar2"}), frozendict({"baz": "bat2"})),
                )
            }
        )
    )

    res = parse_import_specifications(
        (Path(TEST_EXCEL_FILE), Path(TEST_MOCK_CSV_FILE_NAME)), resolver, logger
    )

    assert res == ParseResults(
        frozendict(
            {
                "type1": ParseResult(
                    specification_source(TEST_EXCEL_FILE, "tab1"),
                    (frozendict({"foo": "bar"}), frozendict({"baz": "bat"})),
                ),
                "type2": ParseResult(
                    specification_source(TEST_EXCEL_FILE, "tab2"),
                    (frozendict({"whee": "whoo"}),),  # tuple!
                ),
                "type_other": ParseResult(
                    specification_source(TEST_MOCK_CSV_FILE_NAME),
                    (frozendict({"foo": "bar2"}), frozendict({"baz": "bat2"})),
                ),
            }
        )
    )

    resolver.assert_has_calls(
        [call(Path(TEST_EXCEL_FILE)), call(Path(TEST_MOCK_CSV_FILE_NAME))]
    )
    parser1.assert_called_once_with(Path(TEST_EXCEL_FILE))
    parser2.assert_called_once_with(Path(TEST_MOCK_CSV_FILE_NAME))
    logger.assert_not_called()


def test_parse_import_specifications_fail_no_paths():
    res = parse_import_specifications(tuple(), lambda p: None, lambda e: None)
    assert res == ParseResults(errors=tuple([Error(ErrorType.NO_FILES_PROVIDED)]))


def test_parse_import_specification_resolver_exception():
    """
    This tests an "oh shit" error scenario where we get a completely unexpected error that
    gets caught in the top level catch block and we bail out.
    """
    resolver, logger, parser1 = _get_mocks(3)

    resolver.side_effect = [_ftr(parser1), ArithmeticError("crapsticks")]

    # test that other errors aren't included in the result
    parser1.return_value = ParseResults(errors=tuple([Error(ErrorType.OTHER, "foo")]))

    res = parse_import_specifications(
        (Path(TEST_EXCEL_FILE), Path(TEST_MOCK_CSV_FILE_NAME)), resolver, logger
    )

    assert res == ParseResults(errors=tuple([Error(ErrorType.OTHER, "crapsticks")]))

    resolver.assert_has_calls(
        [call(Path(TEST_EXCEL_FILE)), call(Path(TEST_MOCK_CSV_FILE_NAME))]
    )
    parser1.assert_called_once_with(Path(TEST_EXCEL_FILE))
    # In [1]: ArithmeticError("a") == ArithmeticError("a")
    # Out[1]: False
    # so assert_called_once_with doesn't work
    assert_exception_correct(logger.call_args[0][0], ArithmeticError("crapsticks"))


def test_parse_import_specification_unsupported_type_and_parser_error():
    """
    This test really tests 4 things:
    1. a parser returning an error and that error showing up in the final results
    2. an invalid file type being submitted and having an error show up in the final results
    3. results from a parser being ignored if an error is produced
    4. errors from multiple sources being integrated into the final results
    It's not possible to split the test up further and still test #4
    """
    resolver, logger, parser1, parser2 = _get_mocks(4)

    resolver.side_effect = [_ftr(parser1), _ftr(parser2), _ftr(notype="JPEG")]

    # check that other errors are also returned, and the results are ignored
    parser1.return_value = ParseResults(
        errors=tuple(
            [
                Error(ErrorType.OTHER, "foo"),
                Error(
                    ErrorType.FILE_NOT_FOUND, source_1=specification_source("foo.csv")
                ),
            ]
        )
    )
    parser2.return_value = ParseResults(
        frozendict(
            {
                "foo": ParseResult(
                    specification_source("a"), tuple([frozendict({"a": "b"})])
                )
            }
        )
    )

    res = parse_import_specifications(
        (Path(TEST_EXCEL_FILE), Path(TEST_MOCK_CSV_FILE_NAME), Path("x.jpeg")),
        resolver,
        logger,
    )

    assert res == ParseResults(
        errors=tuple(
            [
                Error(ErrorType.OTHER, "foo"),
                Error(
                    ErrorType.FILE_NOT_FOUND, source_1=specification_source("foo.csv")
                ),
                Error(
                    ErrorType.PARSE_FAIL,
                    "JPEG is not a supported file type for import specifications",
                    specification_source("x.jpeg"),
                ),
            ]
        )
    )

    resolver.assert_has_calls(
        [
            call(Path(TEST_EXCEL_FILE)),
            call(Path(TEST_MOCK_CSV_FILE_NAME)),
            call(Path("x.jpeg")),
        ]
    )
    parser1.assert_called_once_with(Path(TEST_EXCEL_FILE))
    parser2.assert_called_once_with(Path(TEST_MOCK_CSV_FILE_NAME))
    logger.assert_not_called()


def test_parse_import_specification_multiple_specs_and_parser_error():
    """
    This test really tests 4 things:
    1. a parser returning an error and that error showing up in the final results
    2. two specifications for the same data type being submitted and having an error show up
       in the final results
    3. results from a parser being ignored if an error is produced
    4. errors from multiple sources being integrated into the final results
    It's not possible to split the test up further and still test #4
    """
    resolver, logger, parser1, parser2, parser3 = _get_mocks(5)

    resolver.side_effect = [_ftr(parser1), _ftr(parser2), _ftr(parser3)]

    # check that other errors are also returned, and the results are ignored
    parser1.return_value = ParseResults(
        errors=tuple(
            [
                Error(ErrorType.OTHER, "other"),
                Error(
                    ErrorType.FILE_NOT_FOUND,
                    source_1=specification_source(TEST_EXCEL_FILE),
                ),
            ]
        )
    )
    parser2.return_value = ParseResults(
        frozendict(
            {
                "foo": ParseResult(
                    specification_source("a1"), tuple([frozendict({"a": "b"})])
                ),
                "bar": ParseResult(
                    specification_source("b1"), tuple([frozendict({"a": "b"})])
                ),
                "baz": ParseResult(
                    specification_source("c1"), tuple([frozendict({"a": "b"})])
                ),
            },
        )
    )
    parser3.return_value = ParseResults(
        frozendict(
            {
                "foo2": ParseResult(
                    specification_source("a2"), tuple([frozendict({"a": "b"})])
                ),
                "bar": ParseResult(
                    specification_source("b2"), tuple([frozendict({"a": "b"})])
                ),
                "baz": ParseResult(
                    specification_source("c2"), tuple([frozendict({"a": "b"})])
                ),
            },
        )
    )

    res = parse_import_specifications(
        (Path(TEST_EXCEL_FILE), Path(TEST_MOCK_CSV_FILE_NAME), Path("x.tsv")),
        resolver,
        logger,
    )

    assert res == ParseResults(
        errors=tuple(
            [
                Error(ErrorType.OTHER, "other"),
                Error(
                    ErrorType.FILE_NOT_FOUND,
                    source_1=specification_source(TEST_EXCEL_FILE),
                ),
                Error(
                    ErrorType.MULTIPLE_SPECIFICATIONS_FOR_DATA_TYPE,
                    "Data type bar appears in two importer specification sources",
                    specification_source("b1"),
                    specification_source("b2"),
                ),
                Error(
                    ErrorType.MULTIPLE_SPECIFICATIONS_FOR_DATA_TYPE,
                    "Data type baz appears in two importer specification sources",
                    specification_source("c1"),
                    specification_source("c2"),
                ),
            ]
        )
    )

    resolver.assert_has_calls(
        [
            call(Path(TEST_EXCEL_FILE)),
            call(Path(TEST_MOCK_CSV_FILE_NAME)),
            call(Path("x.tsv")),
        ]
    )
    parser1.assert_called_once_with(Path(TEST_EXCEL_FILE))
    parser2.assert_called_once_with(Path(TEST_MOCK_CSV_FILE_NAME))
    parser3.assert_called_once_with(Path("x.tsv"))
    logger.assert_not_called()
