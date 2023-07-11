""" Unit tests for the metadata handling routines. """

import json
import uuid
from collections.abc import Generator
from pathlib import Path as PyPath

from pytest import fixture

from staging_service.metadata import some_metadata
from staging_service.utils import Path
from tests.test_app import FileUtil


@fixture(scope="module", name="temp_dir")
def temp_dir_fixture() -> Generator[PyPath, None, None]:
    with FileUtil() as fu:
        childdir = PyPath(fu.make_dir(str(uuid.uuid4()))).resolve()

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
    target = Path(
        str(temp_dir / "full"),
        str(temp_dir / "meta"),
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
        "lineCount": "5",
        "name": "myfilename",
        "path": "user_path",
        "size": 1280,
    }


def make_test_lines(start, stop):
    return [str(i) + "a" * (256 - len(str(i)) - 1) + "\n" for i in range(start, stop)]
