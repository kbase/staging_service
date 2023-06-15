""" Unit tests for the metadata handling routines. """

import json
import os
import random
import string
import uuid
from collections.abc import Generator
from pathlib import Path

from aiohttp import web
from pytest import fixture, raises

from staging_service.metadata import (
    FILE_SNIPPET_SIZE,
    NOT_TEXT_FILE_VALUE,
    SOURCE_JGI_IMPORT,
    _determine_source,
    _file_read_from_head,
    _file_read_from_tail,
    is_text_string,
    some_metadata,
)
from staging_service.utils import StagingPath
from tests.test_helpers import FileUtil


@fixture(scope="function", name="temp_dir")
def temp_dir_fixture() -> Generator[Path, None, None]:
    """
    A fixture to generate a unique subdirectory within the DATA_DIR
    directory set in the test configuration (which defaults to the "data"
    directory in the root of the repo)
    """
    with FileUtil() as fu:
        childdir = Path(fu.make_dir(str(uuid.uuid4()))).resolve()

        yield childdir

    # FileUtil will auto delete after exiting


async def test_incomplete_metadata_file_update(temp_dir: Path):
    """
    Tests the case where a file is listed or checked for existence prior to completing
    upload, and then an UPA is added to the file. This previously caused incomplete metadata
    to be returned as the logic for whether to run the metadata regeneration code based on
    the contents of the current metadata file was incorrect.
    See https://kbase-jira.atlassian.net/browse/PTV-1767
    """
    await _incomplete_metadata_file_update(
        temp_dir, {"source": "some place", "UPA": "1/2/3"}, "some place"
    )

    await _incomplete_metadata_file_update(temp_dir, {"UPA": "1/2/3"}, "Unknown")


async def _incomplete_metadata_file_update(temp_dir, metadict, source):
    target = StagingPath(
        os.path.join(temp_dir, "full"),
        os.path.join(temp_dir, "meta"),
        "user_path",
        "myfilename",
        "super_fake_jgi_path",
    )

    with open(target.full_path, "w", encoding="utf-8") as p:
        p.writelines(make_test_lines(1, 6))

    with open(target.metadata_path, "w", encoding="utf-8") as p:
        p.write(json.dumps(metadict))

    res = await some_metadata(target)

    assert "mtime" in res  # just check the file time is there
    del res["mtime"]

    assert res == {
        "source": source,
        "md5": "9f07da9655223b777121141ff7735f25",
        "head": "".join(make_test_lines(1, 5)),
        "tail": "".join(make_test_lines(2, 6)),
        "UPA": "1/2/3",
        "isFolder": False,
        "lineCount": 5,
        "name": "myfilename",
        "path": "user_path",
        "size": 1280,
    }


def make_test_lines(start, stop):
    return [str(i) + "a" * (256 - len(str(i)) - 1) + "\n" for i in range(start, stop)]


async def _generate_binary_file(temp_dir):
    target = StagingPath(
        os.path.join(temp_dir, "full"),
        os.path.join(temp_dir, "meta"),
        "user_path",
        "myfilename",
        "",
    )
    with open(target.full_path, "wb") as data_file:
        data_file.write(b"\0\1\2\3")

    res = await some_metadata(target)

    assert "mtime" in res
    assert isinstance(res["mtime"], int)
    assert "lineCount" in res
    assert res["lineCount"] is None
    assert res["head"] == NOT_TEXT_FILE_VALUE
    assert res["tail"] == NOT_TEXT_FILE_VALUE


async def test_binary_data(temp_dir: Path):
    """
    Test case in which metadata is generated for a binary file.
    """
    await _generate_binary_file(temp_dir)


def test_is_text():
    should_be_text = b"hello I'm text"
    should_not_be_text = b"\0\1\2\4"
    is_almost_text = b"hello \0oops"
    text_with_acceptable_control_characters = b"hello\tthis \nis a\rstring"
    invalid_unicode = b"\ac2\xa3"

    assert is_text_string(should_be_text) is True
    assert is_text_string(text_with_acceptable_control_characters) is True
    assert is_text_string(should_not_be_text) is False
    assert is_text_string(is_almost_text) is False
    assert is_text_string(invalid_unicode) is False


async def test_determine_source_jgi_metadata_source_exists(temp_dir: Path):
    staging_path = StagingPath(
        os.path.join(temp_dir, "full"),
        os.path.join(temp_dir, "meta"),
        "user_path",
        "myfilename",
        os.path.join(temp_dir, "jgi_metadata"),
    )

    # In this test, the actual data doesn't matter, just the
    # fact that a file exists.
    with open(staging_path.jgi_metadata, "w", encoding="utf-8") as data_file:
        data_file.write("foo")

    assert _determine_source(staging_path) == SOURCE_JGI_IMPORT


def _create_validated_staging_path(staging_dir: str, file_path: str):
    # Model actual usage, in which we have:
    # - a user
    # - a directory dedicated to user data - each user has a subdirectory
    #   inside it with the name the same as their username
    # - a directory dedicated to metadata, parallel to the data dir
    # - some file, which is the target of our path
    username = "some_user"
    data_dir = os.path.join(staging_dir, "data")
    metadata_dir = os.path.join(staging_dir, "metadata")

    # Must create the data directory for the user, as the
    # jgi metadata file lives IN the data dir (even though KBase
    # metadata files live in the metadata parallel directory)
    os.makedirs(os.path.join(data_dir, username, os.path.dirname(file_path)))

    # Here we "configure" the class. Note that this is global for the class.
    StagingPath._DATA_DIR = data_dir
    StagingPath._META_DIR = metadata_dir

    # Note that "validate_path" does not actually validate the path,
    # it just populates the object with the various paths based on
    # the config above, the username, and a file, possibly on a path.
    return StagingPath.validate_path(username, file_path)


def test_determine_source_jgi_metadata_source_exists_canonical(temp_dir: Path):
    """
    Tests the case of a simple, top level file.
    """
    file_path = "foo.bar"
    filename_base = os.path.basename(file_path)
    staging_path = _create_validated_staging_path(temp_dir, file_path)
    with open(staging_path.jgi_metadata, "w", encoding="utf-8") as data_file:
        data_file.write(f".{staging_path.full_path}.{filename_base}jgi")

    assert _determine_source(staging_path) == SOURCE_JGI_IMPORT


def test_determine_source_jgi_metadata_source_exists_canonical_subdir(temp_dir: Path):
    """
    Tests the case of a file in a subdirectory
    """
    file_path = "some/foo.bar"
    filename_base = os.path.basename(file_path)
    staging_path = _create_validated_staging_path(temp_dir, file_path)
    with open(staging_path.jgi_metadata, "w", encoding="utf-8") as data_file:
        data_file.write(f".{staging_path.full_path}.{filename_base}jgi")

    assert _determine_source(staging_path) == SOURCE_JGI_IMPORT


def test_determine_source_jgi_metadata_source_exists_canonical_deepsubdir(
    temp_dir: Path,
):
    """
    Tests the case of a file in a deeply nested directory
    """
    file_path = "some/deep/dark/scary/foo.bar"
    filename_base = os.path.basename(file_path)
    staging_path = _create_validated_staging_path(temp_dir, file_path)
    with open(staging_path.jgi_metadata, "w", encoding="utf-8") as data_file:
        data_file.write(f".{staging_path.full_path}.{filename_base}jgi")

    assert _determine_source(staging_path) == SOURCE_JGI_IMPORT


def test_determine_source_jgi_metadata_source_doesnt_exist(temp_dir: StagingPath):
    #
    # The _determine_source logic tests if the jgi_metadata exists for this
    # StagingPath object. Unfortunately, it currently tests if the file indicated
    # by the string exists and is a file. It always checks if the file exists,
    # so it must be populated by SOME string.
    #
    # This may seem strange, but the reason is that a StagingPath is NEVER created
    # with the constructor in the code itself, as we do here. It is always
    # constructed by it's own methods, the only two methods it has, which
    # blindly construct the path the file, whether it exists or not.
    #
    # I really don't quite understand this design, but that is the way it is,
    # for now.
    #
    # So the conditions under which "no jgi metadata" is determined are:
    # - path which is not associated with a file or directory (not found)
    # - path associated with a directory
    #
    values_that_indicate_no_jgi_import_metadata_file = [
        "",  # common case of leaving it empty if no metadata file possible
        "zzz",  # nonsensical file name
        os.path.join(
            temp_dir, "jgi_metadata"
        ),  # in the right place, but we still doesn't exist
        os.path.join(temp_dir),  # a directory
    ]
    for invalid_path in values_that_indicate_no_jgi_import_metadata_file:
        staging_path = StagingPath(
            os.path.join(temp_dir, "full"),
            os.path.join(temp_dir, "meta"),
            "user_path",
            "myfilename",
            invalid_path,
        )
        assert _determine_source(staging_path) == "Unknown"


@fixture(scope="function")
def temp_dir2() -> Generator[Path, None, None]:
    with FileUtil() as fu:
        childdir = Path(fu.make_dir(str(uuid.uuid4()))).resolve()

        yield childdir


def make_random_string(string_length: str) -> str:
    random.seed(42)
    possible_letters = string.ascii_letters
    return "".join(
        random.choice(possible_letters) for _ in range(string_length)  # NOSONAR nosec
    )


def test_read_from_head_happy(tmp_path: Path):
    """
    In which we read a text snippet successfully from the front of the file.
    """
    cases = [1, 10, 100, 1000, 10000, 100000]
    # we just happen to know this from metadata.py...
    snippet_length = FILE_SNIPPET_SIZE
    for case in cases:
        file_path = os.path.join(tmp_path, "happy_head.txt")
        file_content = make_random_string(case)
        with open(file_path, "w", encoding="utf-8") as output_file:
            output_file.write(file_content)
        snippet = _file_read_from_head(file_path)
        assert snippet == file_content[:snippet_length]


def test_read_from_tail_happy(tmp_path: Path):
    """
    In which we read a text snippet successfully from the tail of the file.
    """
    cases = [1, 10, 100, 1000, 10000, 100000]
    # we just happen to know this from metadata.py...
    snippet_length = FILE_SNIPPET_SIZE
    for case in cases:
        file_path = os.path.join(tmp_path, "happy_tail.txt")
        file_content = make_random_string(case)
        with open(file_path, "w", encoding="utf-8") as output_file:
            output_file.write(file_content)
        snippet = _file_read_from_tail(file_path)
        assert snippet == file_content[-snippet_length:]


def test_read_from_head_sad(tmp_path: Path):
    """
    In which we attempt to read a snippet from a non-text (binary)
    file, and get the default "error" string.
    """
    cases = [b"\ac2\xa3"]
    # we just happen to know this from metadata.py...
    # snippet_length = 1024
    for case in cases:
        file_path = os.path.join(tmp_path, "sad_head.txt")
        file_content = case
        with open(file_path, "wb") as output_file:
            output_file.write(file_content)
        snippet = _file_read_from_head(file_path)
        assert snippet == NOT_TEXT_FILE_VALUE


def test_read_from_tail_sad(tmp_path: Path):
    """
    In which we attempt to read a snippet from a non-text (binary)
    file, and get the default "error" string.
    """
    cases = [b"\ac2\xa3"]
    # we just happen to know this from metadata.py...
    # snippet_length = 1024
    for case in cases:
        file_path = os.path.join(tmp_path, "sad_tail.txt")
        file_content = case
        with open(file_path, "wb") as output_file:
            output_file.write(file_content)
        snippet = _file_read_from_tail(file_path)
        assert snippet == NOT_TEXT_FILE_VALUE


async def test_invalid_desired_fields(temp_dir: Path):
    staging_path = StagingPath(
        os.path.join(temp_dir, "full"),
        os.path.join(temp_dir, "meta"),
        "user_path",
        "myfilename",
        "",
    )

    with open(staging_path.full_path, "w", encoding="utf-8") as p:
        p.write("foo")

    with raises(web.HTTPBadRequest) as ex:
        await some_metadata(staging_path, ["foo"])
    assert str(ex.value) == "Bad Request"
    # Okay, not a lovely error message, but it is what it is, and should be improved.
    assert ex.value.text == "no data exists for key ('foo',)"
