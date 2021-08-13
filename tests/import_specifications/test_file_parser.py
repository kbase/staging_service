# not much point in testing data classes unless there's custom logic in them

from frozendict import frozendict
from pytest import raises
from tests.test_utils import assert_exception_correct
from pathlib import Path
from typing import Callable

from staging_service.import_specifications.file_parser import (
    PRIMITIVE_TYPE,
    ErrorType,
    FileTypeResolution,
    SpecificationSource,
    Error,
    ParseResult,
    ParseResults,
)


def spcsrc(path: str, tab: str=None):
    return SpecificationSource(Path(path), tab)


def test_SpecificationSource_init_success():
    # minimal
    ss = SpecificationSource(Path("foo"))

    assert ss.file == Path("foo")
    assert ss.tab is None

    # all
    ss = SpecificationSource(Path("bar"), "tabbytab")

    assert ss.file == Path("bar")
    assert ss.tab == "tabbytab"


def test_SpecificationSource_init_fail():
    # could inline this, but might as well follow the same pattern as all the other tests
    specificationSource_init_fail(None, ValueError("file is required"))


def specificationSource_init_fail(file_: str, expected: Exception):
    with raises(Exception) as got:
        SpecificationSource(file_)
    assert_exception_correct(got.value, expected)


def test_FileTypeResolution_init_w_parser_success():
    p = lambda path: ParseResults(errors=(Error(ErrorType.OTHER, "foo"),))
    ftr = FileTypeResolution(p)

    assert ftr.parser is p  # Here only identity equality makes sense
    assert ftr.unsupported_type is None


def test_FileTypeResolution_init_w_unsupported_type_success():
    ftr = FileTypeResolution(unsupported_type="sys")

    assert ftr.parser is None
    assert ftr.unsupported_type == "sys"


def test_FileTypeResolution_init_fail():
    err = "Exectly one of parser or unsupported_type must be supplied"
    pr = ParseResults(errors=(Error(ErrorType.OTHER, "foo"),))
    fileTypeResolution_init_fail(None, None, ValueError(err))
    fileTypeResolution_init_fail(lambda path: pr, "mp-2", ValueError(err))


def fileTypeResolution_init_fail(
    parser: Callable[[Path], ParseResults],
    unexpected_type: str,
    expected: Exception
):
    with raises(Exception) as got:
        FileTypeResolution(parser, unexpected_type)
    assert_exception_correct(got.value, expected)


def test_Error_init_w_FILE_NOT_FOUND_success():
    # minimal
    e = Error(ErrorType.FILE_NOT_FOUND, source_1=spcsrc("foo"))

    assert e.error == ErrorType.FILE_NOT_FOUND
    assert e.message is None
    assert e.source_1 == spcsrc("foo")
    assert e.source_2 is None

    # all
    e = Error(ErrorType.FILE_NOT_FOUND, message="bar", source_1=spcsrc("foo"))

    assert e.error == ErrorType.FILE_NOT_FOUND
    assert e.message == "bar"
    assert e.source_1 == spcsrc("foo")
    assert e.source_2 is None


def test_Error_init_w_PARSE_FAIL_success():
    e = Error(ErrorType.PARSE_FAIL, message="foo", source_1=spcsrc("foo2"))

    assert e.error == ErrorType.PARSE_FAIL
    assert e.message == "foo"
    assert e.source_1 == spcsrc("foo2")
    assert e.source_2 is None


def test_Error_init_w_MULTIPLE_SPECIFICATIONS_FOR_DATA_TYPE_success():
    e = Error(
        ErrorType.MULTIPLE_SPECIFICATIONS_FOR_DATA_TYPE, "foo", spcsrc("foo2"), spcsrc("yay")
    )

    assert e.error == ErrorType.MULTIPLE_SPECIFICATIONS_FOR_DATA_TYPE
    assert e.message == "foo"
    assert e.source_1 == spcsrc("foo2")
    assert e.source_2 == spcsrc("yay")


def test_Error_init_w_NO_FILES_PROVIDED_success():
    e = Error(ErrorType.NO_FILES_PROVIDED)

    assert e.error == ErrorType.NO_FILES_PROVIDED
    assert e.message is None
    assert e.source_1 is None
    assert e.source_2 is None


def test_Error_init_w_ILLEGAL_FILE_NAME_success():
    # minimal
    e = Error(ErrorType.ILLEGAL_FILE_NAME, message="foo")

    assert e.error == ErrorType.ILLEGAL_FILE_NAME
    assert e.message == "foo"
    assert e.source_1 is None
    assert e.source_2 is None

    # all
    e = Error(ErrorType.ILLEGAL_FILE_NAME, message="foo", source_1=spcsrc("wooo"))

    assert e.error == ErrorType.ILLEGAL_FILE_NAME
    assert e.message == "foo"
    assert e.source_1 == spcsrc("wooo")
    assert e.source_2 is None


def test_Error_init_w_OTHER_success():
    # minimal
    e = Error(ErrorType.OTHER, message="foo")

    assert e.error == ErrorType.OTHER
    assert e.message == "foo"
    assert e.source_1 is None
    assert e.source_2 is None

    # all
    e = Error(ErrorType.OTHER, message="foo", source_1=spcsrc("wooo"))

    assert e.error == ErrorType.OTHER
    assert e.message == "foo"
    assert e.source_1 == spcsrc("wooo")
    assert e.source_2 is None


def test_Error_init_fail():
    # arguments are error type, message string, 1st source, 2nd source, exception
    error_init_fail(None, None, None, None, ValueError("error is required"))
    error_init_fail(ErrorType.FILE_NOT_FOUND, None, None, None, ValueError(
        "source_1 is required for a FILE_NOT_FOUND error"))
    err = "message, source_1 is required for a PARSE_FAIL error"
    error_init_fail(ErrorType.PARSE_FAIL, None, spcsrc("wooo"), None, ValueError(err))
    error_init_fail(ErrorType.PARSE_FAIL, "msg", None, None, ValueError(err))
    ms = ErrorType.MULTIPLE_SPECIFICATIONS_FOR_DATA_TYPE
    err = ("message, source_1, source_2 is required for a "
        + "MULTIPLE_SPECIFICATIONS_FOR_DATA_TYPE error")
    error_init_fail(ms, None, None, None, ValueError(err))
    error_init_fail(ms, None, spcsrc("foo"), spcsrc("bar"), ValueError(err))
    error_init_fail(ms, "msg", None, spcsrc("bar"), ValueError(err))
    error_init_fail(ms, "msg", spcsrc("foo"), None, ValueError(err))
    error_init_fail(ErrorType.ILLEGAL_FILE_NAME, None, None, None, ValueError(
        "message is required for a ILLEGAL_FILE_NAME error"))
    error_init_fail(ErrorType.OTHER, None, None, None, ValueError(
        "message is required for a OTHER error"))


def error_init_fail(
    errortype: ErrorType,
    message: str,
    source_1: SpecificationSource,
    source_2: SpecificationSource,
    expected: Exception
):
    with raises(Exception) as got:
        Error(errortype, message, source_1, source_2)
    assert_exception_correct(got.value, expected)


def test_ParseResult_init_success():
    pr = ParseResult(spcsrc("bar"), (frozendict({"foo": "bar"}),))

    assert pr.source == spcsrc("bar")
    assert pr.result == (frozendict({"foo": "bar"}),)


def test_ParseResult_init_fail():
    parseResult_init_fail(None, None, ValueError("source is required"))
    parseResult_init_fail(None, (frozendict({"foo": "bar"}),), ValueError("source is required"))
    parseResult_init_fail(spcsrc("foo"), None, ValueError("result is required"))


def parseResult_init_fail(
    source: SpecificationSource,
    result: tuple[frozendict[str, PRIMITIVE_TYPE]],
    expected: Exception
):
    with raises(Exception) as got:
        ParseResult(source, result)
    assert_exception_correct(got.value, expected)


PR_RESULTS = frozendict({"data_type": ParseResult(
    spcsrc("some_file", "tab"),
    (frozendict({"fasta_file": "foo.fa", "do_thing": 1}),)  # make a tuple!
)})

PR_ERROR = (
    Error(ErrorType.OTHER, message="foo"),
    Error(ErrorType.PARSE_FAIL, message="bar", source_1=spcsrc("some_file", "tab3"))
)

def test_ParseResults_init_w_results_success():
    results_copy = frozendict(PR_RESULTS)  # prevent identity equality

    pr = ParseResults(PR_RESULTS)
    assert pr.results == results_copy
    assert pr.errors is None

    assert pr == ParseResults(results_copy)


def test_ParseResults_init_w_error_success():
    errors_copy = tuple(PR_ERROR) # prevent identity equality

    pr = ParseResults(errors=PR_ERROR)
    assert pr.results is None
    assert pr.errors == errors_copy

    assert pr == ParseResults(errors=errors_copy)


def test_ParseResults_init_fail():
    err = 'Exectly one of results or errors must be supplied'
    parseResults_init_fail(None, None, ValueError(err))
    parseResults_init_fail(PR_RESULTS, PR_ERROR, ValueError(err))


def parseResults_init_fail(
    results: frozendict[str, ParseResult],
    errors: tuple[Error],
    expected: Exception
):
    with raises(Exception) as got:
        ParseResults(results, errors)
    assert_exception_correct(got.value, expected)

