# not much point in testing data classes unless there's custom logic in them

from frozendict import frozendict
from pytest import raises
from tests.test_utils import assert_exception_correct
from pathlib import Path

from staging_service.import_specifications.file_parser import (
    ErrorType,
    SupportedFileType,
    FileTypeResolution,
    PathDef,
    SpecificationSource,
    Error,
    ParseResults,
)

def spcsrc(path, upath, tab=None):
    return SpecificationSource(PathDef(Path(path), Path(upath)), tab)


def test_FileTypeResolution_init_w_type_success():
    ftr = FileTypeResolution(SupportedFileType.CSV)

    assert ftr.type == SupportedFileType.CSV
    assert ftr.unsupported_type is None


def test_FileTypeResolution_init_w_unsupported_type_success():
    ftr = FileTypeResolution(unsupported_type="sys")

    assert ftr.type is None
    assert ftr.unsupported_type == "sys"


def test_FileTypeResolution_init_fail():
    err = "Exectly one of type or unsupported_type must be supplied"
    fileTypeResolution_init_fail(None, None, ValueError(err))
    fileTypeResolution_init_fail(SupportedFileType.CSV, "mp-2", ValueError(err))


def fileTypeResolution_init_fail(type_, utype, expected):
    with raises(Exception) as got:
        FileTypeResolution(type_, utype)
    assert_exception_correct(got.value, expected)


def test_Error_init_w_FILE_NOT_FOUND_success():
    # minimal
    e = Error(ErrorType.FILE_NOT_FOUND, source=spcsrc("foo", "bar"))

    assert e.error == ErrorType.FILE_NOT_FOUND
    assert e.message is None
    assert e.source == spcsrc("foo", "bar")

    # all
    e = Error(ErrorType.FILE_NOT_FOUND, message="bar", source=spcsrc("foo", "bar"))

    assert e.error == ErrorType.FILE_NOT_FOUND
    assert e.message == "bar"
    assert e.source == spcsrc("foo", "bar")


def test_Error_init_w_PARSE_FAIL_success():
    e = Error(ErrorType.PARSE_FAIL, message="foo", source=spcsrc("foo2", "bar"))

    assert e.error == ErrorType.PARSE_FAIL
    assert e.message == "foo"
    assert e.source == spcsrc("foo2", "bar")


def test_Error_init_w_OTHER_success():
    # minimal
    e = Error(ErrorType.OTHER, message="foo")

    assert e.error == ErrorType.OTHER
    assert e.message == "foo"
    assert e.source == None

    # all
    e = Error(ErrorType.OTHER, message="foo", source=spcsrc("wooo", "bar"))

    assert e.error == ErrorType.OTHER
    assert e.message == "foo"
    assert e.source == spcsrc("wooo", "bar")


def test_Error_init_fail():
    error_init_fail(ErrorType.FILE_NOT_FOUND, None, None, ValueError(
        "source is required for a FILE_NOT_FOUND error"))
    err = "source and message are required for a PARSE_FAIL error"
    error_init_fail(ErrorType.PARSE_FAIL, None, spcsrc("wooo", "bar"), ValueError(err))
    error_init_fail(ErrorType.PARSE_FAIL, "msg", None, ValueError(err))
    error_init_fail(ErrorType.OTHER, None, None, ValueError(
        "message is required for a OTHER error"))


def error_init_fail(errortype, message, source, expected):
    with raises(Exception) as got:
        Error(errortype, message, source)
    assert_exception_correct(got.value, expected)


PR_RESULTS = frozendict({"data_type": (spcsrc("some_file", "user_file", "tab"), (
    frozendict({"fasta_file": "foo.fa", "do_thing": 1}),  # make a tuple!
))})

PR_ERROR = (
    Error(ErrorType.OTHER, message="foo"),
    Error(ErrorType.PARSE_FAIL, message="bar", source=spcsrc("some_file", "ufile", "tab3"))
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


def parseResults_init_fail(results, errors, expected):
    with raises(Exception) as got:
        ParseResults(results, errors)
    assert_exception_correct(got.value, expected)

