import uuid

from collections.abc import Generator
from pathlib import Path
from pytest import raises, fixture
from tests.test_app import FileUtil

from staging_service.import_specifications.file_writers import (
    write_csv,
    write_tsv,
)

from tests.test_utils import assert_exception_correct


@fixture(scope="module")
def temp_dir() -> Generator[Path, None, None]:
    with FileUtil() as fu:
        childdir = Path(fu.make_dir(str(uuid.uuid4()))).resolve()

        yield childdir

    # FileUtil will auto delete after exiting


_TEST_DATA = {
    "type1": {
        "order_and_display": [
            ("id1", "thing,with,comma"),
            ("id2", "other"),
            ("id3", "thing\twith\ttabs"),
        ],
        "data": [
            {"id3": "comma,comma", "id1": "yay!\ttab", "id2": 42},
            {"id3": 56.78, "id1": "boo!", "id2": None},
        ]
    },
    "type2": {
        "order_and_display": [
            ("id1", "oh no I only have one column"),
        ],
        "data": [
            {"id1": "foo"},
            {"id1": 0},
        ]
    },
    "type3": {
        "order_and_display": [
            ("some_id", "hey this"),
            ("tab\tid", "xsv is only"),
            ("comma,id", "a template"),
        ],
        "data": []
    }
}

def test_noop():
    assert write_csv(Path("."), {}) == {}
    assert write_tsv(Path("."), {}) == {}

def test_write_csv(temp_dir: Path):
    res = write_csv(temp_dir, _TEST_DATA)
    assert res == {
        "type1": temp_dir / "type1.csv",
        "type2": temp_dir / "type2.csv",
        "type3": temp_dir / "type3.csv",
    }
    _check_contents(
        temp_dir / "type1.csv",
        [
            "Data type: type1; Columns: 3; Version: 1\n",
            "id1,id2,id3\n",
            '"thing,with,comma",other,thing\twith\ttabs\n',
            'yay!\ttab,42,"comma,comma"\n',
            "boo!,,56.78\n",
        ]
    )
    _check_contents(
        temp_dir / "type2.csv",
        [
            "Data type: type2; Columns: 1; Version: 1\n",
            "id1\n",
            "oh no I only have one column\n",
            "foo\n",
            "0\n",
        ]
    )
    _check_contents(
        temp_dir / "type3.csv",
        [
            "Data type: type3; Columns: 3; Version: 1\n",
            'some_id,tab\tid,"comma,id"\n',
            "hey this,xsv is only,a template\n",
        ]
    )


def test_write_tsv(temp_dir: Path):
    res = write_tsv(temp_dir, _TEST_DATA)
    assert res == {
        "type1": temp_dir / "type1.tsv",
        "type2": temp_dir / "type2.tsv",
        "type3": temp_dir / "type3.tsv",
    }
    _check_contents(
        temp_dir / "type1.tsv",
        [
            "Data type: type1; Columns: 3; Version: 1\n",
            "id1\tid2\tid3\n",
            'thing,with,comma\tother\t"thing\twith\ttabs"\n',
            '"yay!\ttab"\t42\tcomma,comma\n',
            "boo!\t\t56.78\n",
        ]
    )
    _check_contents(
        temp_dir / "type2.tsv",
        [
            "Data type: type2; Columns: 1; Version: 1\n",
            "id1\n",
            "oh no I only have one column\n",
            "foo\n",
            "0\n",
        ]
    )
    _check_contents(
        temp_dir / "type3.tsv",
        [
            "Data type: type3; Columns: 3; Version: 1\n",
            'some_id\t"tab\tid"\tcomma,id\n',
            "hey this\txsv is only\ta template\n",
        ]
    )


def _check_contents(file: Path, lines: list[str]):
    with open(file) as f:
        assert f.readlines() == lines


def test_file_writers_fail():
    p = Path()
    file_writers_fail(None, {}, ValueError("The folder cannot be null"))
    file_writers_fail(p, None, ValueError("The types value must be a mapping"))
    file_writers_fail(
        p, {None: 1}, ValueError("A data type cannot be a non-string or a whitespace only string"))
    file_writers_fail(
        p,
        {"  \t ": 1},
        ValueError("A data type cannot be a non-string or a whitespace only string"))
    file_writers_fail(p, {"t": []}, ValueError("The value for data type t must be a mapping"))
    file_writers_fail(p, {"t": 1}, ValueError("The value for data type t must be a mapping"))
    file_writers_fail(p, {"t": {}}, ValueError("Data type t missing order_and_display key"))
    file_writers_fail(
        p,
        {"t": {"order_and_display": {}, "data": []}},
        ValueError("Data type t order_and_display value is not a list"))
    file_writers_fail(
        p,
        {"t": {"order_and_display": [], "data": []}},
        ValueError("At least one entry is required for order_and_display for type t"))
    file_writers_fail(
        p,
        {"t": {"order_and_display": [["foo", "bar"]]}},
        ValueError("Data type t missing data key"))
    file_writers_fail(
        p,
        {"t": {"order_and_display": [["foo", "bar"]], "data": "foo"}},
        ValueError("Data type t data value is not a list"))
    file_writers_fail(
        p,
        {"t": {"order_and_display": [["foo", "bar"], "baz"] , "data": []}},
        ValueError("Invalid order_and_display entry for datatype t at index 1 - "
                   + "the entry is not a list"))
    file_writers_fail(
        p,
        {"t": {"order_and_display": [("foo", "bar"), ["whee", "whoo"], ["baz"]] , "data": []}},
        ValueError("Invalid order_and_display entry for datatype t at index 2 - "
                   + "expected 2 item list"))
    file_writers_fail(
        p,
        {"t": {"order_and_display": [("foo", "bar", "whee"), ["whee", "whoo"]] , "data": []}},
        ValueError("Invalid order_and_display entry for datatype t at index 0 - "
                   + "expected 2 item list"))
    for parm in [None, "  \t   ", 1]:
        file_writers_fail(
            p,
            {"t": {"order_and_display": [(parm, "foo"), ["whee", "whoo"]], "data": []}},
            ValueError("Invalid order_and_display entry for datatype t at index 0 - "
                    + "parameter ID cannot be a non-string or a whitespace only string"))
        file_writers_fail(
            p,
            {"t": {"order_and_display": [("bar", "foo"), ["whee", parm]], "data": []}},
            ValueError("Invalid order_and_display entry for datatype t at index 1 - "
                    + "parameter display name cannot be a non-string or a whitespace only string"))
    file_writers_fail(
        p,
        {"t": {"order_and_display": [("bar", "foo"), ["whee", "whoo"]], "data": ["foo"]}},
        ValueError("Data type t data row 0 is not a mapping"))
    file_writers_fail(
        p,
        {"t": {"order_and_display": [("bar", "foo")], "data": [{"bar": 1}, []]}},
        ValueError("Data type t data row 1 is not a mapping"))
    file_writers_fail(
        p,
        {"t": {"order_and_display": [("foo", "bar"), ["whee", "whoo"]],
               "data": [{"foo": 1, "whee": 2}, {"foo": 2}]}},
        ValueError("Data type t data row 1 does not have the same keys as order_and_display"))
    file_writers_fail(
        p,
        {"ty": {"order_and_display": [("foo", "bar"), ["whee", "whoo"]],
                "data": [{"foo": 2, "whee": 3, 5: 4}, {"foo": 1, "whee": 2}]}},
        ValueError("Data type ty data row 0 does not have the same keys as order_and_display"))
    file_writers_fail(
        p,
        {"ty": {"order_and_display": [("foo", "bar"), ["whee", "whoo"]],
                "data": [{"foo": 2, "whee": 3}, {"foo": 1, "whee": []}]}},
        ValueError("Data type ty data row 1's value for parameter whee "
                   + "is not a number or a string"))



def file_writers_fail(path: Path, types: dict, expected: Exception):
    with raises(Exception) as got:
        write_csv(path, types)
    assert_exception_correct(got.value, expected)
    with raises(Exception) as got:
        write_tsv(path, types)
    assert_exception_correct(got.value, expected)