# not much point in testing data classes unless there's custom logic in them

from frozendict import frozendict
from pytest import raises
from tests.test_utils import assert_exception_correct

from staging_service.import_specifications.file_parser import (
    ErrorType,
    SpecificationSource,
    ParseResults,
)

PR_RESULTS = frozendict({"data_type": (SpecificationSource("some_file", "tab"), (
    frozendict({"fasta_file": "foo.fa", "do_thing": 1}),  # make a tuple!
))})

PR_ERROR = frozendict({
    SpecificationSource("some_file"): "ah crehp",
    SpecificationSource("other_file", "tab3"): "that sucks bro",
})

def test_ParseResults_init_w_results_success():
    results_copy = frozendict(PR_RESULTS)  # prevent identity equality

    pr = ParseResults(PR_RESULTS)
    assert pr.results == results_copy
    assert pr.errortype is None
    assert pr.errors is None

    assert pr == ParseResults(results_copy)


def test_ParseResults_init_w_error_success():
    errors_copy = frozendict(PR_ERROR) # prevent identity equality

    pr = ParseResults(errortype=ErrorType.PARSE_FAIL, errors=PR_ERROR)
    assert pr.results is None
    assert pr.errortype == ErrorType.PARSE_FAIL
    assert pr.errors == errors_copy

    assert pr == ParseResults(errortype=ErrorType.PARSE_FAIL, errors=errors_copy)


def test_ParseResults_init_fail():
    parseResults_init_fail(None, None, None, ValueError(
        "At least one of results or errors are required"))
    parseResults_init_fail(PR_RESULTS, ErrorType.OTHER, None, ValueError(
        "Cannot include both results and errors"))
    parseResults_init_fail(PR_RESULTS, None, PR_ERROR, ValueError(
        "Cannot include both results and errors"))
    parseResults_init_fail(None, ErrorType.OTHER, None, ValueError(
        "Both or neither of the errortype and error are required"))
    parseResults_init_fail(None, None, PR_ERROR, ValueError(
        "Both or neither of the errortype and error are required"))


def parseResults_init_fail(results, errortype, errors, expected):
    with raises(Exception) as got:
        ParseResults(results, errortype, errors)
    assert_exception_correct(got.value, expected)

