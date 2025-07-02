import asyncio
import configparser
import hashlib
import json
import os
import platform
import uuid
import jsonschema
import pytest
import shutil
import string
import time
from io import BytesIO
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlencode

import openpyxl
import pandas
from aiohttp import FormData, test_utils
from hypothesis import given, settings
from hypothesis import strategies as st

import staging_service.app as app
from staging_service.config import StagingServiceConfig
import staging_service.globus as globus
import staging_service.utils as utils
from staging_service.AutoDetectUtils import AutoDetectUtils
from tests.test_utils import check_excel_contents, check_file_contents

TEST_TOKEN = os.environ.get("KBASE_TEST_TOKEN")
TEST_USER = os.environ.get("KBASE_TEST_USER")

if os.environ.get("KB_DEPLOYMENT_CONFIG") is None:
    from tests.test_utils import bootstrap

    bootstrap()

decoder = json.JSONDecoder()

config = StagingServiceConfig(os.environ["KB_DEPLOYMENT_CONFIG"])

utils.Path._DATA_DIR = config.data_dir
utils.Path._META_DIR = config.meta_dir
AUTH_URL = config.auth_url

# config = configparser.ConfigParser()
# config.read(os.environ["KB_DEPLOYMENT_CONFIG"])

# DATA_DIR = config["staging_service"]["DATA_DIR"]
# META_DIR = config["staging_service"]["META_DIR"]
# AUTH_URL = config["staging_service"]["AUTH_URL"]
# if DATA_DIR.startswith("."):
#     DATA_DIR = os.path.normpath(os.path.join(os.getcwd(), DATA_DIR))
# if META_DIR.startswith("."):
#     META_DIR = os.path.normpath(os.path.join(os.getcwd(), META_DIR))
# utils.Path._DATA_DIR = DATA_DIR
# utils.Path._META_DIR = META_DIR


def asyncgiven(**kwargs):
    """alternative to hypothesis.given decorator for async"""

    def real_decorator(fn):
        @given(**kwargs)
        def aio_wrapper(*args, **kwargs):
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            future = asyncio.wait_for(fn(*args, **kwargs), timeout=60)
            loop.run_until_complete(future)

        return aio_wrapper

    return real_decorator


async def mock_globus_app(config: configparser.ConfigParser):
    application = await app.app_factory(config)

    async def mock_globus_id(*args, **kwargs):
        return ["testuser@globusid.org"]

    globus._get_globus_ids = mock_globus_id  # TODO this doesn't allow testing of this fn does it
    return application


class AppClient:
    @classmethod
    async def create(
        cls,
        config: configparser.ConfigParser,
        auth_token: str | None,
        cookies: dict[str, str] | None = None,
    ) -> "AppClient":
        """
        Creating this with an auth token sets the headers call by default to use the
        provided auth token in the Authorization header.
        If you want to make a call with a different header, you can
        do so by setting headers directly in the call.
        """
        app = await mock_globus_app(config)
        server = test_utils.TestServer(app)
        return AppClient(server, auth_token, cookies)

    def __init__(
        self, server: test_utils.TestServer, auth_token: str | None, cookies: dict[str, str] | None
    ):
        self.server = server
        self.auth_token = auth_token
        self.cookies = cookies

    async def __aenter__(self) -> test_utils.TestClient:
        await self.server.start_server(loop=asyncio.get_event_loop())
        headers = {}
        if self.auth_token is not None:
            headers["Authorization"] = self.auth_token
        self.client = test_utils.TestClient(
            self.server, loop=asyncio.get_event_loop(), headers=headers, cookies=self.cookies
        )
        return self.client

    async def __aexit__(self, *args):
        await self.server.close()
        await self.client.close()


class FileUtil:
    def __init__(self, base_dir=config.data_dir):
        self.base_dir = base_dir

    def __enter__(self):
        os.makedirs(self.base_dir, exist_ok=True)
        shutil.rmtree(self.base_dir)
        os.makedirs(self.base_dir, exist_ok=False)
        return self

    def __exit__(self, *args):
        shutil.rmtree(self.base_dir)

    def make_file(self, path, contents):
        path = os.path.join(self.base_dir, path)
        with open(path, encoding="utf-8", mode="w") as f:
            f.write(contents)
        return path

    def make_dir(self, path):
        path = os.path.join(self.base_dir, path)
        os.makedirs(path, exist_ok=True)
        return path

    def remove_dir(self, path):
        shutil.rmtree(path)


first_letter_alphabet = [c for c in string.ascii_lowercase + string.ascii_uppercase]
username_alphabet = [
    c for c in "_" + string.ascii_lowercase + string.ascii_uppercase + string.digits
]
username_strat = st.text(max_size=99, min_size=1, alphabet=username_alphabet)
username_first_strat = st.text(max_size=1, min_size=1, alphabet=first_letter_alphabet)


#
# BEGIN TESTS
#


@given(username_first_strat, username_strat)
def test_path_cases(username_first, username_rest):
    username = username_first + username_rest
    assert username + "/foo/bar" == utils.Path.validate_path(username, "foo/bar").user_path
    assert username + "/baz" == utils.Path.validate_path(username, "foo/../bar/../baz").user_path
    assert username + "/bar" == utils.Path.validate_path(username, "foo/../../../../bar").user_path
    assert username + "/foo" == utils.Path.validate_path(username, "./foo").user_path
    assert username + "/foo/bar" == utils.Path.validate_path(username, "../foo/bar").user_path
    assert username + "/foo" == utils.Path.validate_path(username, "/../foo").user_path
    assert username + "/" == utils.Path.validate_path(username, "/foo/..").user_path
    assert username + "/foo" == utils.Path.validate_path(username, "/foo/.").user_path
    assert username + "/foo" == utils.Path.validate_path(username, "foo/").user_path
    assert username + "/foo" == utils.Path.validate_path(username, "foo").user_path
    assert username + "/foo" == utils.Path.validate_path(username, "/foo/").user_path
    assert username + "/foo" == utils.Path.validate_path(username, "/foo").user_path
    assert username + "/foo" == utils.Path.validate_path(username, "foo/.").user_path
    assert username + "/" == utils.Path.validate_path(username, "").user_path
    assert username + "/" == utils.Path.validate_path(username, "foo/..").user_path
    assert username + "/" == utils.Path.validate_path(username, "/..../").user_path
    assert username + "/stuff.ext" == utils.Path.validate_path(username, "/stuff.ext").user_path


@given(username_first_strat, username_strat, st.text())
def test_path_sanitation(username_first, username_rest, path):
    username = username_first + username_rest
    validated = utils.Path.validate_path(username, path)
    assert validated.full_path.startswith(config.data_dir)
    assert validated.user_path.startswith(username)
    assert validated.metadata_path.startswith(config.meta_dir)
    assert validated.full_path.find("/..") == -1
    assert validated.user_path.find("/..") == -1
    assert validated.metadata_path.find("/..") == -1
    assert validated.full_path.find("../") == -1
    assert validated.user_path.find("../") == -1
    assert validated.metadata_path.find("../") == -1


@asyncgiven(txt=st.text())
async def test_cmd(txt):
    with FileUtil(config.data_dir) as fs:
        d = fs.make_dir("test")
        assert "" == await utils.run_command("ls", d)
        f = fs.make_file("test/test2", txt)
        md5 = hashlib.md5(txt.encode("utf8")).hexdigest()
        this_system = platform.system()
        if this_system == "Linux":
            md52 = await utils.run_command("md5sum", f)
            expected_md5 = md52.split()[0]
        elif this_system == "Darwin":
            md52 = await utils.run_command("md5", f)
            expected_md5 = md52.split()[3]

        assert md5 == expected_md5


async def do_auth_test(
    token: str | None, cookies: dict[str, str] | None, expected_status: int, expected_text: str
):
    async with await AppClient.create(config, token, cookies=cookies) as cli:
        resp = await cli.get("/test-auth")
        assert resp.status == expected_status
        text = await resp.text()
        assert expected_text in text


async def test_auth():
    await do_auth_test(TEST_TOKEN, None, 200, f"I'm authenticated as {TEST_USER}")


@pytest.mark.parametrize("cookie_name", ["kbase_session", "kbase_session_backup"])
async def test_auth_cookies(cookie_name):
    await do_auth_test(None, {cookie_name: TEST_TOKEN}, 200, f"I'm authenticated as {TEST_USER}")


@pytest.mark.parametrize("token", [None, ""])
async def test_auth_fail_no_token(token):
    await do_auth_test(token, None, 401, "must provide an auth token")


async def test_auth_fail_bad_token():
    await do_auth_test("bad_token", None, 401, "token is invalid")


@pytest.mark.parametrize("cookie_name", ["kbase_session", "kbase_session_backup"])
async def test_auth_fail_bad_cookie_token(cookie_name):
    await do_auth_test(None, {cookie_name: "bad_token"}, 401, "token is invalid")


async def test_auth_fail_service_err():
    # Not sure how to test this, as the service should fail on startup with a bad auth URL
    # TODO: configure a local auth server with bad data to test this
    pass


async def test_service():
    async with await AppClient.create(config, TEST_TOKEN) as cli:
        resp = await cli.get("/test-service")
        assert resp.status == 200
        text = await resp.text()
        assert "staging service version" in text


async def test_jgi_metadata():
    txt = "testing text\n"
    jgi_metadata = '{"file_owner": "sdm", "added_date": "2013-08-12T00:21:53.844000"}'

    async with await AppClient.create(config, TEST_TOKEN) as cli:
        with FileUtil() as fs:
            fs.make_dir(os.path.join(TEST_USER, "test"))
            fs.make_file(os.path.join(TEST_USER, "test", "test_jgi.fastq"), txt)
            fs.make_file(os.path.join(TEST_USER, "test", ".test_jgi.fastq.jgi"), jgi_metadata)
            res1 = await cli.get(os.path.join("jgi-metadata", "test", "test_jgi.fastq"))
            assert res1.status == 200
            json_text = await res1.text()
            json = decoder.decode(json_text)
            expected_keys = ["file_owner", "added_date"]
            assert set(json.keys()) >= set(expected_keys)
            assert json.get("file_owner") == "sdm"
            assert json.get("added_date") == "2013-08-12T00:21:53.844000"

            # testing non-existing jbi metadata file
            res1 = await cli.get(
                os.path.join("jgi-metadata", "test", "non_existing.1617.2.1467.fastq")
            )
            assert res1.status == 404


async def test_metadata():
    txt = "testing text\n"
    async with await AppClient.create(config, TEST_TOKEN) as cli:
        with FileUtil() as fs:
            fs.make_dir(os.path.join(TEST_USER, "test"))
            fs.make_file(os.path.join(TEST_USER, "test", "test_file_1"), txt)
            res1 = await cli.get(os.path.join("metadata", "test", "test_file_1"))
            assert res1.status == 200
            json_text = await res1.text()
            json = decoder.decode(json_text)
            expected_keys = [
                "source",
                "md5",
                "lineCount",
                "head",
                "tail",
                "name",
                "path",
                "mtime",
                "size",
                "isFolder",
            ]
            assert set(json.keys()) >= set(expected_keys)
            assert json.get("source") == "Unknown"
            assert json.get("md5") == "e9018937ab54e6ce88b9e2dfe5053095"
            assert json.get("lineCount") == "1"
            assert json.get("head") == "testing text\n"
            assert json.get("tail") == "testing text\n"
            assert json.get("name") == "test_file_1"
            assert json.get("size") == 13
            assert not json.get("isFolder")

            # testing existing metadata file
            res2 = await cli.get(
                os.path.join("metadata", "test", "test_file_1"),
            )
            assert res2.status == 200
            json_text = await res2.text()
            json = decoder.decode(json_text)
            expected_keys = [
                "source",
                "md5",
                "lineCount",
                "head",
                "tail",
                "name",
                "path",
                "mtime",
                "size",
                "isFolder",
            ]
            assert set(json.keys()) >= set(expected_keys)
            assert json.get("source") == "Unknown"
            assert json.get("md5") == "e9018937ab54e6ce88b9e2dfe5053095"
            assert json.get("lineCount") == "1"
            assert json.get("head") == "testing text\n"
            assert json.get("tail") == "testing text\n"
            assert json.get("name") == "test_file_1"
            assert json.get("size") == 13
            assert not json.get("isFolder")

            # testing corrupted metadata file
            path = os.path.join(config.meta_dir, TEST_USER, "test", "test_file_1")
            with open(path, encoding="utf-8", mode="w") as f:
                f.write('{"source": "Unknown"}')
            res3 = await cli.get(
                os.path.join("metadata", "test", "test_file_1"),
            )
            assert res3.status == 200
            json_text = await res3.text()
            json = decoder.decode(json_text)
            expected_keys = [
                "source",
                "md5",
                "lineCount",
                "head",
                "tail",
                "name",
                "path",
                "mtime",
                "size",
                "isFolder",
            ]
            assert set(json.keys()) >= set(expected_keys)
            assert json.get("source") == "Unknown"
            assert json.get("md5") == "e9018937ab54e6ce88b9e2dfe5053095"
            assert json.get("lineCount") == "1"
            assert json.get("head") == "testing text\n"
            assert json.get("tail") == "testing text\n"
            assert json.get("name") == "test_file_1"
            assert json.get("size") == 13
            assert not json.get("isFolder")


async def test_define_upa():
    txt = "testing text\n"
    async with await AppClient.create(config, TEST_TOKEN) as cli:
        with FileUtil() as fs:
            fs.make_dir(os.path.join(TEST_USER, "test"))
            fs.make_file(os.path.join(TEST_USER, "test", "test_file_1"), txt)
            # generating metadata file
            res1 = await cli.get(
                os.path.join("metadata", "test", "test_file_1"),
            )
            assert res1.status == 200

            # posting UPA
            res2 = await cli.post(
                os.path.join("define-upa", "test", "test_file_1"),
                data={"UPA": "test_UPA"},
            )
            assert res2.status == 200
            json_text = await res2.text()
            assert "successfully updated UPA test_UPA" in json_text

            # getting new metadata
            res3 = await cli.get(
                os.path.join("metadata", "test", "test_file_1"),
            )
            assert res3.status == 200
            json_text = await res3.text()
            json = decoder.decode(json_text)
            expected_keys = [
                "source",
                "md5",
                "lineCount",
                "head",
                "tail",
                "name",
                "path",
                "mtime",
                "size",
                "isFolder",
                "UPA",
            ]
            assert set(json.keys()) >= set(expected_keys)
            assert json.get("source") == "Unknown"
            assert json.get("md5") == "e9018937ab54e6ce88b9e2dfe5053095"
            assert json.get("lineCount") == "1"
            assert json.get("head") == "testing text\n"
            assert json.get("tail") == "testing text\n"
            assert json.get("name") == "test_file_1"
            assert json.get("size") == 13
            assert not json.get("isFolder")
            assert json.get("UPA") is not None
            assert json.get("UPA") == "test_UPA"

            # testing non-existing jbi metadata file
            res4 = await cli.post(
                os.path.join("define-upa", "test", "non_existing.test_file_1"),
                data={"UPA": "test_UPA"},
            )
            assert res4.status == 404

            # testing missing body
            res5 = await cli.post(os.path.join("define-upa", "test", "test_file_1"))
            assert res5.status == 400

            # testing missing UPA in body
            res6 = await cli.post(
                os.path.join("define-upa", "test", "test_file_1"),
                data={"missing_UPA": "test_UPA"},
            )
            assert res6.status == 400


async def test_mv():
    txt = "testing text\n"
    async with await AppClient.create(config, TEST_TOKEN) as cli:
        with FileUtil() as fs:
            fs.make_dir(os.path.join(TEST_USER, "test"))
            fs.make_file(os.path.join(TEST_USER, "test", "test_file_1"), txt)

            # list current test directory
            res1 = await cli.get(
                os.path.join("list", "test"),
            )
            assert res1.status == 200
            json_text = await res1.text()
            json = decoder.decode(json_text)
            assert len(json) == 1
            assert json[0]["name"] == "test_file_1"

            res2 = await cli.patch(
                os.path.join("mv", "test", "test_file_1"),
                data={"newPath": "test/test_file_2"},
            )
            assert res2.status == 200
            json_text = await res2.text()
            assert "successfully moved" in json_text

            # relist test directory
            res3 = await cli.get(
                os.path.join("list", "test"),
            )
            assert res3.status == 200
            json_text = await res3.text()
            json = decoder.decode(json_text)
            assert len(json) == 1
            assert json[0]["name"] == "test_file_2"

            # testing missing body
            res5 = await cli.patch(
                os.path.join("mv", "test", "test_file_1"),
            )
            assert res5.status == 400

            # testing missing newPath in body
            res6 = await cli.patch(
                os.path.join("mv", "test", "test_file_1"),
                data={"missing_newPath": "test/test_file_2"},
            )
            assert res6.status == 400

            # testing moving to existing file
            res7 = await cli.patch(
                os.path.join("mv", "test", "test_file_2"),
                data={"newPath": "test/test_file_2"},
            )
            assert res7.status == 409

            # testing non-existing file
            res7 = await cli.patch(
                os.path.join("mv", "test", "non_existing.test_file_2"),
                data={"newPath": "test/test_file_2"},
            )
            assert res7.status == 404


async def test_delete():
    txt = "testing text\n"
    async with await AppClient.create(config, TEST_TOKEN) as cli:
        with FileUtil() as fs:
            fs.make_dir(os.path.join(TEST_USER, "test"))
            fs.make_file(os.path.join(TEST_USER, "test", "test_file_1"), txt)

            # list current test directory
            res1 = await cli.get(
                os.path.join("list", "test"),
            )
            assert res1.status == 200
            json_text = await res1.text()
            json = decoder.decode(json_text)
            assert len(json) == 1
            assert json[0]["name"] == "test_file_1"

            res2 = await cli.delete(
                os.path.join("delete", "test", "test_file_1"),
            )
            assert res2.status == 200
            json_text = await res2.text()
            assert "successfully deleted" in json_text

            # relist test directory
            res3 = await cli.get(
                os.path.join("list", "test"),
            )
            assert res3.status == 200
            json_text = await res3.text()
            json = decoder.decode(json_text)
            assert len(json) == 0

            # testing non-existing file
            res5 = await cli.delete(
                os.path.join("delete", "test", "non_existing.test_file_2"),
            )
            assert res5.status == 404


async def test_list():
    txt = "testing text"
    async with await AppClient.create(config, TEST_TOKEN) as cli:
        with FileUtil() as fs:
            fs.make_dir(os.path.join(TEST_USER, "test"))
            fs.make_file(os.path.join(TEST_USER, "test", "test_file_1"), txt)
            fs.make_dir(os.path.join(TEST_USER, "test", "test_sub_dir"))
            fs.make_file(os.path.join(TEST_USER, "test", "test_sub_dir", "test_file_2"), txt)
            res1 = await cli.get("list/..")
            assert res1.status == 404
            res2 = await cli.get(
                os.path.join("list", "test", "test_file_1"),
            )
            assert res2.status == 400

            # testing root directory with 'list/' routes
            res3 = await cli.get("/list/")
            assert res3.status == 200
            json_text = await res3.text()
            json = decoder.decode(json_text)
            file_folder_count = [file_json["isFolder"] for file_json in json]
            assert json[0]["isFolder"] is True
            assert json[0]["name"] == "test"
            assert json[0]["path"] == f"{TEST_USER}/test"
            assert json[0]["mtime"] <= time.time() * 1000
            assert len(file_folder_count) == 4  # 2 folders and 2 files
            assert sum(file_folder_count) == 2

            # testing root directory with 'list' route
            res4 = await cli.get("/list")
            assert res4.status == 200
            json_text = await res4.text()
            json = decoder.decode(json_text)
            file_folder_count = [file_json["isFolder"] for file_json in json]
            assert json[0]["isFolder"] is True
            assert json[0]["name"] == "test"
            assert json[0]["path"] == f"{TEST_USER}/test"
            assert json[0]["mtime"] <= time.time() * 1000
            assert len(file_folder_count) == 4  # 2 folders and 2 files
            assert sum(file_folder_count) == 2

            # testing sub-directory
            res5 = await cli.get(os.path.join("list", "test"))
            assert res5.status == 200
            json_text = await res5.text()
            json = decoder.decode(json_text)
            file_folder_count = [file_json["isFolder"] for file_json in json]
            # 1 sub-directory, 1 file in sub-directory and 1 file in root
            assert len(file_folder_count) == 3
            assert sum(file_folder_count) == 1

            # testing list dot-files
            fs.make_file(
                os.path.join(TEST_USER, "test", ".test_file_1"),  # NOSONAR python:S1192
                txt,
            )
            # f5 = fs.make_file(os.path.join(username, 'test', '.globus_id'), txt)
            res6 = await cli.get("/list/")
            assert res6.status == 200
            json_text = await res6.text()
            json = decoder.decode(json_text)

            file_names = [file_json["name"] for file_json in json if not file_json["isFolder"]]
            assert ".test_file_1" not in file_names  # NOSONAR python:S1192
            assert ".globus_id" not in file_names
            assert len(file_names) == 2

            # testing list showHidden option
            res7 = await cli.get("/list/", params={"showHidden": "True"})
            assert res7.status == 200
            json_text = await res7.text()
            json = decoder.decode(json_text)
            file_names = [file_json["name"] for file_json in json if not file_json["isFolder"]]
            assert ".test_file_1" in file_names  # NOSONAR python:S1192
            assert ".globus_id" in file_names
            assert len(file_names) == 4


# remove deadline from hypothesis, since this test can be laggy and lead to false-negative fails
@settings(deadline=None)
@asyncgiven(txt=st.text())
async def test_download(txt):
    async with await AppClient.create(config, TEST_TOKEN) as cli:
        with FileUtil() as fs:
            fs.make_dir(os.path.join(TEST_USER, "test"))
            fs.make_file(os.path.join(TEST_USER, "test", "test_file_1"), txt)

            res = await cli.get(
                os.path.join("download", "test", "test_file_1"),
            )
            assert res.status == 200
            result_text = await res.read()
            assert result_text == txt.encode()


async def test_download_errors():
    async with await AppClient.create(config, TEST_TOKEN) as cli:
        with FileUtil() as fs:
            fs.make_dir(os.path.join(TEST_USER, "test"))

            res1 = await cli.get(
                "dwnload",
            )
            assert res1.status == 404
            res2 = await cli.get(
                os.path.join("download", "test", ""),
            )
            assert res2.status == 400


async def test_similar():
    txt = "testing text"
    async with await AppClient.create(config, TEST_TOKEN) as cli:
        with FileUtil() as fs:
            fs.make_dir(os.path.join(TEST_USER, "test"))
            fs.make_file(os.path.join(TEST_USER, "test", "test_file_1.fq"), txt)
            fs.make_dir(os.path.join(TEST_USER, "test", "test_sub_dir"))
            fs.make_file(os.path.join(TEST_USER, "test", "test_sub_dir", "test_file_2.fq"), txt)
            fs.make_file(
                os.path.join(TEST_USER, "test", "test_sub_dir", "test_file_right.fq"),
                txt,
            )
            fs.make_file(os.path.join(TEST_USER, "test", "test_sub_dir", "my_files"), txt)

            # testing similar file name
            res1 = await cli.get("similar/test/test_file_1.fq")
            assert res1.status == 200
            json_text = await res1.text()
            json = decoder.decode(json_text)
            assert len(json) == 2
            assert json[0].get("name") in ["test_file_2.fq", "test_file_right.fq"]
            assert json[1].get("name") in ["test_file_2.fq", "test_file_right.fq"]

            # testing non-existing file
            res2 = await cli.get("similar/test/non-existing")
            assert res2.status == 404

            # testing path is a directory
            res3 = await cli.get("similar/test")
            assert res3.status == 400


async def test_existence():
    txt = "testing text"
    async with await AppClient.create(config, TEST_TOKEN) as cli:
        with FileUtil() as fs:
            fs.make_dir(os.path.join(TEST_USER, "test"))
            fs.make_file(os.path.join(TEST_USER, "test", "test_file_1"), txt)
            fs.make_dir(os.path.join(TEST_USER, "test", "test_sub_dir"))
            fs.make_file(os.path.join(TEST_USER, "test", "test_sub_dir", "test_file_2"), txt)
            fs.make_dir(os.path.join(TEST_USER, "test", "test_sub_dir", "test_file_1"))
            fs.make_dir(os.path.join(TEST_USER, "test", "test_sub_dir", "test_sub_dir"))
            fs.make_file(
                os.path.join(TEST_USER, "test", "test_sub_dir", "test_sub_dir", "test_file_1"),
                txt,
            )

            # testing existence of both file and folder name
            res1 = await cli.get("existence/test_file_1")
            assert res1.status == 200
            json_text = await res1.text()
            json = decoder.decode(json_text)
            assert json["exists"] is True
            assert json["isFolder"] is False

            # testing existence of file
            res2 = await cli.get("existence/test_file_2")
            assert res2.status == 200
            json_text = await res2.text()
            json = decoder.decode(json_text)
            assert json["exists"] is True
            assert json["isFolder"] is False

            # testing existence of folder
            res3 = await cli.get("existence/test_sub_dir")
            assert res3.status == 200
            json_text = await res3.text()
            json = decoder.decode(json_text)
            assert json["exists"] is True
            assert json["isFolder"] is True

            # testing non-existence
            res4 = await cli.get("existence/fake_file")
            assert res4.status == 200
            json_text = await res4.text()
            json = decoder.decode(json_text)
            assert json["exists"] is False
            assert json["isFolder"] is False

            res5 = await cli.get("existence/test_sub")
            assert res5.status == 200
            json_text = await res5.text()
            json = decoder.decode(json_text)
            assert json["exists"] is False
            assert json["isFolder"] is False


async def test_search():
    txt = "testing text"
    async with await AppClient.create(config, TEST_TOKEN) as cli:
        with FileUtil() as fs:
            fs.make_dir(os.path.join(TEST_USER, "test"))
            fs.make_file(os.path.join(TEST_USER, "test", "test1"), txt)
            fs.make_dir(os.path.join(TEST_USER, "test", "test2"))
            fs.make_file(os.path.join(TEST_USER, "test", "test2", "test3"), txt)
            res1 = await cli.get("search/")
            assert res1.status == 200
            json_text = await res1.text()
            json = decoder.decode(json_text)
            assert len(json) == 4
            res2 = await cli.get("search/test1")
            assert res2.status == 200
            json_text = await res2.text()
            json = decoder.decode(json_text)
            assert len(json) == 1
            res3 = await cli.get("search/test2")
            assert res3.status == 200
            json_text = await res3.text()
            json = decoder.decode(json_text)
            assert len(json) == 2


async def test_upload():
    txt = "testing text\n"
    async with await AppClient.create(config, TEST_TOKEN) as cli:
        # testing missing body
        res1 = await cli.post("upload")
        assert res1.status == 400

        with FileUtil() as fs:
            fs.make_dir(os.path.join(TEST_USER, "test"))
            f = fs.make_file(os.path.join(TEST_USER, "test", "test_file_1"), txt)

            files = {"destPath": "/", "uploads": open(f, "rb")}

            res2 = await cli.post(os.path.join("upload"), data=files)

            assert res2.status == 200


async def _upload_file_fail_filename(filename: str, err: str):
    # Note two file uploads in a row causes a test error:
    # https://github.com/aio-libs/aiohttp/issues/3968
    async with await AppClient.create(
        config, TEST_TOKEN
    ) as cli:  # username is ignored by AppClient
        formdata = FormData()
        formdata.add_field("destPath", "/")
        formdata.add_field("uploads", BytesIO(b"sometext"), filename=filename)

        res = await cli.post("upload", data=formdata)

        assert await res.text() == err
        assert res.status == 403


async def test_upload_fail_leading_space():
    await _upload_file_fail_filename(
        " test_file", "cannot upload file with name beginning with space"
    )


async def test_upload_fail_dotfile():
    await _upload_file_fail_filename(
        ".test_file", "cannot upload file with name beginning with '.'"
    )


async def test_upload_fail_comma_in_file():
    await _upload_file_fail_filename("test,file", "cannot upload file with ',' in name")


# remove deadline from hypothesis, since this test can be laggy and lead to false-negative fails
@settings(deadline=None)
@asyncgiven(contents=st.text())
async def test_directory_decompression(contents):
    fname = "test"
    dirname = "dirname"
    path = utils.Path.validate_path(TEST_USER, os.path.join(dirname, fname))
    path2 = utils.Path.validate_path(TEST_USER, os.path.join(dirname, fname))
    if path.user_path.endswith("/") or path2.user_path.endswith("/"):
        # invalid test case
        # TODO it should be faster if hypothesis could generate all cases except these
        return
    methods = [
        ("gztar", ".tgz"),
        ("gztar", ".tar.gz"),
        ("zip", ".zip"),
        ("zip", ".ZIP"),
        ("bztar", ".tar.bz2"),
        ("bztar", ".tar.bz"),
        ("tar", ".tar"),
    ]
    async with await AppClient.create(config, TEST_TOKEN) as cli:
        for method, extension in methods:
            with FileUtil() as fs:
                d = fs.make_dir(os.path.join(TEST_USER, dirname))
                f1 = fs.make_file(path.user_path, contents)
                d2 = fs.make_dir(os.path.join(TEST_USER, dirname, dirname))
                f3 = fs.make_file(path2.user_path, contents)
                # end common test code
                compressed = shutil.make_archive(d, method, d[: -len(dirname)], dirname)
                name = dirname + extension
                if not compressed.endswith(extension):
                    basename, _ = os.path.splitext(compressed)
                    basename, _ = os.path.splitext(basename)
                    # this should handle the .stuff.stuff case as well as .stuff
                    # it won't handle any more though such as .stuff.stuff.stuff
                    new_name = basename + extension
                    os.rename(compressed, new_name)
                    compressed = new_name
                shutil.rmtree(d)
                # check to see that the originals are gone
                assert not os.path.exists(d)
                assert not os.path.exists(f1)
                assert not os.path.exists(d2)
                assert not os.path.exists(f3)
                assert os.path.exists(compressed)
                resp = await cli.patch("/decompress/" + name)
                assert resp.status == 200
                text = await resp.text()
                assert "successfully decompressed" in text
                assert name in text
                # check to see if we got back what we started with for all files and directories
                assert os.path.exists(d)
                assert os.path.exists(d)
                assert os.path.exists(f1)
                assert os.path.exists(d2)
                assert os.path.exists(f3)


# remove deadline from hypothesis, since this test can be laggy and lead to false-negative fails
@settings(deadline=None)
@asyncgiven(contents=st.text())
async def test_file_decompression(contents):
    fname = "test"
    dirname = "dirname"
    path = utils.Path.validate_path(TEST_USER, os.path.join(dirname, fname))
    if path.user_path.endswith("/"):
        # invalid test case
        # TODO it should be faster if hypothesis could generate all cases except these
        return
    methods = [("gzip", ".gz"), ("bzip2", ".bz2")]

    async with await AppClient.create(config, TEST_TOKEN) as cli:
        for method, extension in methods:
            with FileUtil() as fs:
                d = fs.make_dir(os.path.join(TEST_USER, dirname))
                f1 = fs.make_file(path.user_path, contents)
                name = fname + extension
                await utils.run_command(method, f1)
                # check to see that the original is gone
                assert os.path.exists(d)
                assert not os.path.exists(f1)
                assert os.path.exists(os.path.join(d, name))
                resp = await cli.patch(
                    "/decompress/" + os.path.join(dirname, name),
                )
                assert resp.status == 200
                text = await resp.text()
                assert "successfully decompressed" in text
                assert name in text
                # check to see if we got back what we started with for all files and directories
                assert os.path.exists(d)
                assert os.path.exists(f1)


async def test_importer_mappings():
    """
    This tests calling with simple good cases, and some expected bad cases
    :return:
    """
    # Normal case, no match
    data = {"file_list": ["file1.txt"]}
    qs1 = urlencode(data, doseq=True)

    async with await AppClient.create(config, TEST_TOKEN) as cli:
        resp = await cli.get(f"importer_mappings/?{qs1}")
        assert resp.status == 200
        text = await resp.json()
        assert "mappings" in text
        mappings = text["mappings"]
        assert mappings[0] is None

    # Normal case, one match
    data = {"file_list": ["file1.txt", "file.tar.gz"]}
    qs2 = urlencode(data, doseq=True)

    async with await AppClient.create(config, TEST_TOKEN) as cli:
        resp = await cli.get(f"importer_mappings/?{qs2}", data=data)
        assert resp.status == 200
        text = await resp.json()
        assert "mappings" in text
        mappings = text["mappings"]
        assert mappings[0] is None
        # As we update the app mappings this test may need to be changed
        # Or we need to reload json file itself

        # unzip_mapping = AutoDetectUtils._MAPPINGS["apps"]["decompress/unpack"]
        assert mappings[1][0] == AutoDetectUtils.get_mappings_by_extension("gz")["mappings"][0]

    # A dict is passed in
    data = {"file_list": [{}]}
    qs3 = urlencode(data, doseq=True)
    async with await AppClient.create(config, TEST_TOKEN) as cli:
        resp = await cli.get(f"importer_mappings/?{qs3}", data=data)
        assert resp.status == 200
        text = await resp.json()
        assert "mappings" in text
        mappings = text["mappings"]
        assert mappings[0] is None

    # Missing the inputs field
    bad_data = []
    bad_data.append({"apple": [{}]})
    # No files passed in
    bad_data.append({})
    # No files passed in
    bad_data.append({"file_list": []})

    for data in bad_data:
        qsd = urlencode(data, doseq=True)
        async with await AppClient.create(config, TEST_TOKEN) as cli:
            resp = await cli.get(f"importer_mappings/?{qsd}")
            assert resp.status == 400
            text = await resp.text()
            assert f"must provide file_list field. Your provided qs: {unquote(qsd)}" in text


async def test_bulk_specification_success():
    # In other tests a username is passed to AppClient but AppClient completely ignores it...
    async with await AppClient.create(config, TEST_TOKEN) as cli:
        with FileUtil() as fu:
            fu.make_dir(f"{TEST_USER}/somefolder")
            base = Path(fu.base_dir) / TEST_USER
            tsv = "genomes.tsv"
            with open(base / tsv, "w", encoding="utf-8") as f:
                f.writelines(
                    [
                        "Data type: genomes; Columns: 3; Version: 1\n",
                        "spec1\tspec2\t   spec3   \n",
                        "Spec 1\t Spec 2\t Spec 3\n",
                        "val1 \t   ꔆ   \t    7\n",
                        "val3\tval4\t1\n",
                    ]
                )
            csv = "somefolder/breakfastcereals.csv"
            with open(base / csv, "w", encoding="utf-8") as f:
                f.writelines(
                    [
                        "Data type: breakfastcereals; Columns: 3; Version: 1\n",
                        "s1,s2,s3\n",
                        "S 1,S 2,S 3\n",
                        "froot loops ,   puffin   ,   gross\n",
                        "grape nuts , dietary fiber, also gross\n",
                    ]
                )
            excel = "importspec.xlsx"
            # https://github.com/PyCQA/pylint/issues/3060
            # pylint: disable=abstract-class-instantiated
            with pandas.ExcelWriter(base / excel) as exw:
                df = pandas.DataFrame(
                    [
                        ["Data type: fruit_bats; Columns: 2; Version: 1"],
                        ["bat_name", "wing_count"],
                        ["Name of Bat", "Number of wings"],
                        ["George", 42],
                        ["Fred", 1.5],
                    ]
                )
                df.to_excel(exw, sheet_name="bats", header=False, index=False)
                df = pandas.DataFrame(
                    [
                        ["Data type: tree_sloths; Columns: 2; Version: 1"],
                        ["entity_id", "preferred_food"],
                        ["Entity ID", "Preferred Food"],
                        ["That which ends all", "ꔆ"],
                    ]
                )
                df.to_excel(exw, sheet_name="sloths", header=False, index=False)

            resp = await cli.get(f"bulk_specification/?files={tsv}  ,   {csv},  {excel}   ")
            jsn = await resp.json()
            assert jsn == {
                "types": {
                    "genomes": [
                        {"spec1": "val1", "spec2": "ꔆ", "spec3": 7},
                        {"spec1": "val3", "spec2": "val4", "spec3": 1},
                    ],
                    "breakfastcereals": [
                        {"s1": "froot loops", "s2": "puffin", "s3": "gross"},
                        {"s1": "grape nuts", "s2": "dietary fiber", "s3": "also gross"},
                    ],
                    "fruit_bats": [
                        {"bat_name": "George", "wing_count": 42},
                        {"bat_name": "Fred", "wing_count": 1.5},
                    ],
                    "tree_sloths": [{"entity_id": "That which ends all", "preferred_food": "ꔆ"}],
                },
                "files": {
                    "genomes": {"file": f"{TEST_USER}/genomes.tsv", "tab": None},
                    "breakfastcereals": {
                        "file": f"{TEST_USER}/somefolder/breakfastcereals.csv",
                        "tab": None,
                    },
                    "fruit_bats": {"file": f"{TEST_USER}/importspec.xlsx", "tab": "bats"},
                    "tree_sloths": {
                        "file": f"{TEST_USER}/importspec.xlsx",
                        "tab": "sloths",
                    },
                },
            }
            assert resp.status == 200


async def test_bulk_specification_dts_success():
    async with await AppClient.create(config, TEST_TOKEN) as cli:
        with FileUtil() as fu:
            sub_dir = "dts_folder"
            dts_dir = f"{TEST_USER}/{sub_dir}"
            fu.make_dir(dts_dir)
            base = Path(fu.base_dir) / TEST_USER / sub_dir
            manifest_1 = "test_manifest_1.json"
            manifest_1_dict = {
                "resources": [],
                "instructions": {
                    "protocol": "KBase narrative import",
                    "objects": [
                        {
                            "data_type": "gff_metagenome",
                            "parameters": {
                                "fasta_file": "fasta_1",
                                "gff_file": "gff_1",
                                "genome_name": "mg_1",
                            },
                        },
                        {
                            "data_type": "gff_metagenome",
                            "parameters": {
                                "fasta_file": "fasta_2",
                                "gff_file": "gff_2",
                                "genome_name": "mg_2",
                            },
                        },
                    ],
                },
            }
            manifest_2 = "test_manifest_2.json"
            manifest_2_dict = {
                "resources": [],
                "instructions": {
                    "protocol": "KBase narrative import",
                    "objects": [
                        {
                            "data_type": "gff_genome",
                            "parameters": {
                                "fasta_file": "g_fasta_1",
                                "gff_file": "g_gff_1",
                                "genome_name": "genome_1",
                            },
                        },
                        {
                            "data_type": "gff_genome",
                            "parameters": {
                                "fasta_file": "g_fasta_2",
                                "gff_file": "g_gff_2",
                                "genome_name": "genome_2",
                            },
                        },
                    ],
                },
            }
            with open(base / manifest_1, "w", encoding="utf-8") as f:
                json.dump(manifest_1_dict, f)
            with open(base / manifest_2, "w", encoding="utf-8") as f:
                json.dump(manifest_2_dict, f)
            resp = await cli.get(
                f"bulk_specification/?files={sub_dir}/{manifest_1}  ,   {sub_dir}/{manifest_2}&dts"
            )
            jsn = await resp.json()
            assert jsn == {
                "types": {
                    "gff_genome": [
                        {
                            "fasta_file": "g_fasta_1",
                            "gff_file": "g_gff_1",
                            "genome_name": "genome_1",
                        },
                        {
                            "fasta_file": "g_fasta_2",
                            "gff_file": "g_gff_2",
                            "genome_name": "genome_2",
                        },
                    ],
                    "gff_metagenome": [
                        {"fasta_file": "fasta_1", "gff_file": "gff_1", "genome_name": "mg_1"},
                        {"fasta_file": "fasta_2", "gff_file": "gff_2", "genome_name": "mg_2"},
                    ],
                },
                "files": {
                    "gff_metagenome": {"file": f"{TEST_USER}/{sub_dir}/{manifest_1}", "tab": None},
                    "gff_genome": {"file": f"{TEST_USER}/{sub_dir}/{manifest_2}", "tab": None},
                },
            }
            assert resp.status == 200


async def test_bulk_specification_dts_fail_json_without_dts():
    async with await AppClient.create(config, TEST_TOKEN) as cli:
        with FileUtil() as fu:
            sub_dir = "dts_folder"
            dts_dir = f"{TEST_USER}/{sub_dir}"
            fu.make_dir(dts_dir)
            base = Path(fu.base_dir) / TEST_USER / sub_dir
            manifest_1 = "test_manifest_1.json"
            manifest_1_dict = {
                "resources": [],
                "instructions": {
                    "protocol": "KBase narrative import",
                    "objects": [
                        {
                            "data_type": "gff_metagenome",
                            "parameters": {
                                "fasta_file": "fasta_1",
                                "gff_file": "gff_1",
                                "genome_name": "mg_1",
                            },
                        }
                    ],
                },
            }
            with open(base / manifest_1, "w", encoding="utf-8") as f:
                json.dump(manifest_1_dict, f)
            resp = await cli.get(f"bulk_specification/?files={sub_dir}/{manifest_1}")
            jsn = await resp.json()
            assert jsn == {
                "errors": [
                    {
                        "type": "cannot_parse_file",
                        "file": f"{dts_dir}/{manifest_1}",
                        "message": "json is not a supported file type for import specifications",
                        "tab": None,
                    }
                ]
            }
            assert resp.status == 400


async def test_bulk_specification_dts_fail_wrong_format():
    async with await AppClient.create(config, TEST_TOKEN) as cli:
        with FileUtil() as fu:
            sub_dir = "dts_folder"
            dts_dir = f"{TEST_USER}/{sub_dir}"
            fu.make_dir(dts_dir)
            base = Path(fu.base_dir) / TEST_USER / sub_dir
            manifest = "test_manifest.json"
            manifest_data = ["wrong", "format"]
            with open(base / manifest, "w", encoding="utf-8") as f:
                json.dump(manifest_data, f)
            resp = await cli.get(f"bulk_specification/?files={sub_dir}/{manifest}&dts")
            jsn = await resp.json()
            assert jsn == {
                "errors": [
                    {
                        "type": "cannot_parse_file",
                        "file": f"{dts_dir}/{manifest}",
                        "message": "Manifest is not a dictionary",
                        "tab": None,
                    }
                ]
            }
            assert resp.status == 400


@pytest.mark.parametrize(
    "manifest,expected",
    [
        ("test_manifest.foo", "foo"),
        ("json", app.NO_EXTENSION),
        (".json", app.NO_EXTENSION),
        ("some_manifest", app.NO_EXTENSION),
    ],
)
async def test_bulk_specification_dts_fail_wrong_extension(manifest: str, expected: str):
    async with await AppClient.create(config, TEST_TOKEN) as cli:
        with FileUtil() as fu:
            sub_dir = "dts_folder"
            dts_dir = f"{TEST_USER}/{sub_dir}"
            fu.make_dir(dts_dir)
            base = Path(fu.base_dir) / TEST_USER / sub_dir
            manifest_data = {"resources": [], "instructions": {}}
            with open(base / manifest, "w", encoding="utf-8") as f:
                json.dump(manifest_data, f)
            resp = await cli.get(f"bulk_specification/?files={sub_dir}/{manifest}&dts")
            jsn = await resp.json()
            assert jsn == {
                "errors": [
                    {
                        "type": "cannot_parse_file",
                        "file": f"{dts_dir}/{manifest}",
                        "message": f"{expected} is not a supported file type for import specifications",
                        "tab": None,
                    }
                ]
            }
            assert resp.status == 400


def test_bulk_specification_dts_fail_bad_schema():
    # TODO: This is tested manually, as there's no good way to inject bad configs
    # to individual tests right now.
    # TODO: automated tests for:
    # * missing schema config
    # * missing schema file
    # * malformed schema file (i.e. not json)
    # * bad schema (good JSON, invalid as json schema)
    pass


def test_load_and_validate_schema_good():
    # TODO: update this after updating how config is handled
    schema_file = config.dts_manifest_schema
    validator = app.load_and_validate_schema(schema_file)
    assert isinstance(validator, jsonschema.Draft202012Validator)


def test_load_and_validate_schema_missing_file():
    not_real_file = Path(str(uuid.uuid4()))
    # double-check that the file doesn't exist and make a new one if so.
    # shouldn't ever happen, ideally, but easy to check.
    while not_real_file.exists():
        not_real_file = Path(str(uuid.uuid4()))
    with pytest.raises(FileNotFoundError, match="No such file or directory"):
        app.load_and_validate_schema(not_real_file)


def test_load_and_validate_schema_malformed_file(tmp_path: Path):
    # TODO: migrate FileUtil and import_specifications.test_individual_parsers.temp_path_fixture
    # into conftest.py, and resolve everywhere else that FileUtil gets used.
    # Until then, the built-in tmp_path is appropriate for these tests
    wrong_schema = "not valid json"
    schema_file = tmp_path / f"{uuid.uuid4()}.json"
    schema_file.write_text(wrong_schema, encoding="utf-8")
    with pytest.raises(json.JSONDecodeError, match="Expecting value: line 1 column 1"):
        app.load_and_validate_schema(schema_file)


def test_load_and_validate_schema_bad(tmp_path: Path):
    invalid = {"properties": {"some_prop": {"type": "not_real"}}}
    schema_file = tmp_path / f"{uuid.uuid4()}.json"
    schema_file.write_text(json.dumps(invalid), encoding="utf-8")
    exp_err = f"Schema file {schema_file} is not a valid JSON schema: 'not_real' is not valid"
    with pytest.raises(Exception, match=exp_err):
        app.load_and_validate_schema(schema_file)


async def test_bulk_specification_fail_no_files():
    async with await AppClient.create(config, TEST_TOKEN) as cli:
        for f in ["", "?files=", "?files=  ,   ,,   ,  "]:
            resp = await cli.get(f"bulk_specification/{f}")
            jsn = await resp.json()
            assert jsn == {"errors": [{"type": "no_files_provided"}]}
            assert resp.status == 400


async def test_bulk_specification_fail_not_found():
    async with await AppClient.create(config, TEST_TOKEN) as cli:
        with FileUtil() as fu:
            fu.make_dir(f"{TEST_USER}/otherfolder")
            base = Path(fu.base_dir) / TEST_USER
            tsv = "otherfolder/genomes.tsv"
            with open(base / tsv, "w", encoding="utf-8") as f:
                f.writelines(
                    [
                        "Data type: genomes; Columns: 3; Version: 1\n",
                        "spec1\tspec2\t   spec3   \n",
                        "Spec 1\t Spec 2\t Spec 3\n",
                        "val1 \t   ꔆ   \t    7\n",
                    ]
                )
            resp = await cli.get(f"bulk_specification/?files={tsv},somefile.csv")
            jsn = await resp.json()
            assert jsn == {
                "errors": [{"type": "cannot_find_file", "file": f"{TEST_USER}/somefile.csv"}]
            }
            assert resp.status == 404


async def test_bulk_specification_fail_parse_fail():
    """
    Tests a number of different parse fail cases, including incorrect file types.
    Also tests that all the errors are combined correctly.
    """
    async with await AppClient.create(config, TEST_TOKEN) as cli:
        with FileUtil() as fu:
            fu.make_dir(f"{TEST_USER}/otherfolder")
            base = Path(fu.base_dir) / TEST_USER
            tsv = "otherfolder/genomes.tsv"
            # this one is fine
            with open(base / tsv, "w", encoding="utf-8") as f:
                f.writelines(
                    [
                        "Data type: genomes; Columns: 3; Version: 1\n",
                        "spec1\tspec2\t   spec3   \n",
                        "Spec 1\t Spec 2\t Spec 3\n",
                        "val1 \t   ꔆ   \t    7\n",
                    ]
                )
            csv = "otherfolder/thing.csv"
            # this one has a misspelling in the header
            with open(base / csv, "w", encoding="utf-8") as f:
                f.writelines(
                    [
                        "Dater type: breakfastcereals; Columns: 3; Version: 1\n",
                        "s1,s2,s3\n",
                        "S 1,S 2,S 3\n",
                        "froot loops ,   puffin   ,   gross\n",
                    ]
                )
            excel = "stuff.xlsx"
            # https://github.com/PyCQA/pylint/issues/3060
            # pylint: disable=abstract-class-instantiated
            with pandas.ExcelWriter(base / excel) as exw:
                # this one is fine
                df = pandas.DataFrame(
                    [
                        ["Data type: fruit_bats; Columns: 2; Version: 1"],
                        ["bat_name", "wing_count"],
                        ["Name of Bat", "Number of wings"],
                        ["George", 42],
                    ]
                )
                df.to_excel(exw, sheet_name="bats", header=False, index=False)
                # this one is missing a parameter ID
                df = pandas.DataFrame(
                    [
                        ["Data type: tree_sloths; Columns: 2; Version: 1"],
                        ["", "preferred_food"],
                        ["ID", "Foods I like"],
                        ["Kevin Garibaldi", "Beeeaaaaans!"],
                    ]
                )
                df.to_excel(exw, sheet_name="sloths", header=False, index=False)

            # this also tests a number of bad file extensions - no need to create files
            resp = await cli.get(
                f"bulk_specification/?files={tsv},{csv},{excel}"
                + ",badfile,badfile.fasta.gz,badfile.sra,badfile.sys,badfile."
            )
            jsn = await resp.json()
            assert jsn == {
                "errors": [
                    {
                        "type": "cannot_parse_file",
                        "message": 'Invalid header; got "Dater type: breakfastcereals; '
                        + 'Columns: 3; Version: 1", expected "Data type: <data_type>; '
                        + 'Columns: <column count>; Version: <version>"',
                        "file": f"{TEST_USER}/otherfolder/thing.csv",
                        "tab": None,
                    },
                    {
                        "type": "cannot_parse_file",
                        "message": "Missing header entry in row 2, position 1",
                        "file": f"{TEST_USER}/stuff.xlsx",
                        "tab": "sloths",
                    },
                    {
                        "type": "cannot_parse_file",
                        "message": "badfile is not a supported file type for import specifications",
                        "file": f"{TEST_USER}/badfile",
                        "tab": None,
                    },
                    {
                        "type": "cannot_parse_file",
                        "message": "fasta.gz is not a supported file type for import specifications",
                        "file": f"{TEST_USER}/badfile.fasta.gz",
                        "tab": None,
                    },
                    {
                        "type": "cannot_parse_file",
                        "message": "sra is not a supported file type for import specifications",
                        "file": f"{TEST_USER}/badfile.sra",
                        "tab": None,
                    },
                    {
                        "type": "cannot_parse_file",
                        "message": "sys is not a supported file type for import specifications",
                        "file": f"{TEST_USER}/badfile.sys",
                        "tab": None,
                    },
                    {
                        "type": "cannot_parse_file",
                        "message": "badfile. is not a supported file type for import specifications",
                        "file": f"{TEST_USER}/badfile.",
                        "tab": None,
                    },
                ]
            }
            assert resp.status == 400


async def test_bulk_specification_fail_column_count():
    async with await AppClient.create(config, TEST_TOKEN) as cli:
        with FileUtil() as fu:
            fu.make_dir(TEST_USER)
            base = Path(fu.base_dir) / TEST_USER
            tsv = "genomes.tsv"
            # this one is fine
            with open(base / tsv, "w", encoding="utf-8") as f:
                f.writelines(
                    [
                        "Data type: genomes; Columns: 3; Version: 1\n",
                        "spec1\tspec2\t   spec3   \n",
                        "Spec 1\t Spec 2\t Spec 3\n",
                        "val1 \t   ꔆ   \t    7\n",
                    ]
                )
            csv = "thing.csv"
            # this one is missing a column in the last row
            with open(base / csv, "w", encoding="utf-8") as f:
                f.writelines(
                    [
                        "Data type: breakfastcereals; Columns: 3; Version: 1\n",
                        "s1,s2,s3\n",
                        "S 1,S 2,S 3\n",
                        "froot loops ,   puffin\n",
                    ]
                )
            excel = "stuff.xlsx"
            # https://github.com/PyCQA/pylint/issues/3060
            # pylint: disable=abstract-class-instantiated
            with pandas.ExcelWriter(base / excel) as exw:
                # this one has an extra column in the last row
                df = pandas.DataFrame(
                    [
                        ["Data type: fruit_bats; Columns: 2; Version: 1"],
                        ["bat_name", "wing_count"],
                        ["Name of Bat", "Number of wings"],
                        ["George", 42, 56],
                    ]
                )
                df.to_excel(exw, sheet_name="bats", header=False, index=False)
                # this one is fine
                df = pandas.DataFrame(
                    [
                        ["Data type: tree_sloths; Columns: 2; Version: 1"],
                        ["entity_id", "preferred_food"],
                        ["Entity ID", "Preferred Food"],
                        ["That which ends all", "ꔆ"],
                    ]
                )
                df.to_excel(exw, sheet_name="sloths", header=False, index=False)

            resp = await cli.get(f"bulk_specification/?files={tsv},{csv},{excel}")
            jsn = await resp.json()
            assert jsn == {
                "errors": [
                    {
                        "type": "incorrect_column_count",
                        "message": "Incorrect number of items in line 4, expected 3, got 2",
                        "file": f"{TEST_USER}/thing.csv",
                        "tab": None,
                    },
                    {
                        "type": "incorrect_column_count",
                        "message": "Incorrect number of items in line 4, expected 2, got 3",
                        "file": f"{TEST_USER}/stuff.xlsx",
                        "tab": "bats",
                    },
                ]
            }
            assert resp.status == 400


async def test_bulk_specification_fail_multiple_specs_per_type():
    async with await AppClient.create(config, TEST_TOKEN) as cli:
        with FileUtil() as fu:
            fu.make_dir(TEST_USER)
            base = Path(fu.base_dir) / TEST_USER
            tsv = "genomes.tsv"
            # this one is fine
            with open(base / tsv, "w", encoding="utf-8") as f:
                f.writelines(
                    [
                        "Data type: genomes; Columns: 3; Version: 1\n",
                        "spec1\tspec2\t   spec3   \n",
                        "Spec 1\t Spec 2\t Spec 3\n",
                        "val1 \t   ꔆ   \t    7\n",
                    ]
                )
            csv1 = "thing.csv"
            # this is the first of the breakfastcereals data sources, so fine
            with open(base / csv1, "w", encoding="utf-8") as f:
                f.writelines(
                    [
                        "Data type: breakfastcereals; Columns: 3; Version: 1\n",
                        "s1,s2,s3\n",
                        "S 1,S 2,S 3\n",
                        "froot loops ,   puffin, whee\n",
                    ]
                )
            csv2 = "thing2.csv"
            # this data type is also breakfastcereals, so will cause an error
            with open(base / csv2, "w", encoding="utf-8") as f:
                f.writelines(
                    [
                        "Data type: breakfastcereals; Columns: 2; Version: 1\n",
                        "s1,s2\n",
                        "S 1,S 2\n",
                        "froot loops ,   puffin\n",
                    ]
                )
            excel = "stuff.xlsx"
            # https://github.com/PyCQA/pylint/issues/3060
            # pylint: disable=abstract-class-instantiated
            with pandas.ExcelWriter(base / excel) as exw:
                # this data type is also breakfastcereals, so will cause an error
                df = pandas.DataFrame(
                    [
                        ["Data type: breakfastcereals; Columns: 2; Version: 1"],
                        ["bat_name", "wing_count"],
                        ["Name of Bat", "Number of wings"],
                        ["George", 42],
                    ]
                )
                df.to_excel(exw, sheet_name="bats", header=False, index=False)
                # this one is fine
                df = pandas.DataFrame(
                    [
                        ["Data type: tree_sloths; Columns: 2; Version: 1"],
                        ["entity_id", "preferred_food"],
                        ["Entity ID", "Preferred Food"],
                        ["That which ends all", "ꔆ"],
                    ]
                )
                df.to_excel(exw, sheet_name="sloths", header=False, index=False)

            resp = await cli.get(f"bulk_specification/?files={tsv},{csv1},{csv2},{excel}")
            jsn = await resp.json()
            err = "Data type breakfastcereals appears in two importer specification sources"
            assert jsn == {
                "errors": [
                    {
                        "type": "multiple_specifications_for_data_type",
                        "message": err,
                        "file_1": f"{TEST_USER}/thing.csv",
                        "tab_1": None,
                        "file_2": f"{TEST_USER}/thing2.csv",
                        "tab_2": None,
                    },
                    {
                        "type": "multiple_specifications_for_data_type",
                        "message": err,
                        "file_1": f"{TEST_USER}/thing.csv",
                        "tab_1": None,
                        "file_2": f"{TEST_USER}/stuff.xlsx",
                        "tab_2": "bats",
                    },
                ]
            }
            assert resp.status == 400


async def test_bulk_specification_fail_multiple_specs_per_type_excel():
    """
    Test an excel file with an internal data type collision.
    This is the only case when all 5 error fields are filled out.
    """
    async with await AppClient.create(config, TEST_TOKEN) as cli:
        with FileUtil() as fu:
            fu.make_dir(TEST_USER)
            base = Path(fu.base_dir) / TEST_USER
            excel = "stuff.xlsx"
            # https://github.com/PyCQA/pylint/issues/3060
            # pylint: disable=abstract-class-instantiated
            with pandas.ExcelWriter(base / excel) as exw:
                df = pandas.DataFrame(
                    [
                        ["Data type: breakfastcereals; Columns: 2; Version: 1"],
                        ["bat_name", "wing_count"],
                        ["Name of Bat", "Number of wings"],
                        ["George", 42],
                    ]
                )
                df.to_excel(exw, sheet_name="bats", header=False, index=False)
                df = pandas.DataFrame(
                    [
                        ["Data type: tree_sloths; Columns: 2; Version: 1"],
                        ["entity_id", "preferred_food"],
                        ["Entity ID", "Preferred Food"],
                        ["That which ends all", "ꔆ"],
                    ]
                )
                df.to_excel(exw, sheet_name="sloths", header=False, index=False)
                df = pandas.DataFrame(
                    [
                        ["Data type: breakfastcereals; Columns: 2; Version: 1"],
                        ["bat_name", "wing_count"],
                        ["Name of Bat", "Number of wings"],
                        ["George", 42],
                    ]
                )
                df.to_excel(exw, sheet_name="otherbats", header=False, index=False)

            resp = await cli.get(f"bulk_specification/?files={excel}")
            jsn = await resp.json()
            assert jsn == {
                "errors": [
                    {
                        "type": "multiple_specifications_for_data_type",
                        "message": "Found datatype breakfastcereals in multiple tabs",
                        "file_1": f"{TEST_USER}/stuff.xlsx",
                        "tab_1": "bats",
                        "file_2": f"{TEST_USER}/stuff.xlsx",
                        "tab_2": "otherbats",
                    },
                ]
            }
            assert resp.status == 400


_IMPORT_SPEC_TEST_DATA = {
    "genome": {
        "order_and_display": [["id1", "display1"], ["id2", "display2"]],
        "data": [
            {"id1": 54, "id2": "boo"},
            {"id1": 32, "id2": "yikes"},
        ],
    },
    "reads": {
        "order_and_display": [
            ["name", "Reads File Name"],
            ["inseam", "Reads inseam measurement in km"],
        ],
        "data": [
            {"name": "myreads.fa", "inseam": 0.1},
        ],
    },
}


async def test_write_bulk_specification_success_csv():
    # In other tests a username is passed to AppClient but AppClient completely ignores it...
    async with await AppClient.create(config, TEST_TOKEN) as cli:
        with FileUtil() as fu:
            fu.make_dir(TEST_USER)
            resp = await cli.post(
                "write_bulk_specification/",  # NOSONAR
                json={
                    "output_directory": "specs",
                    "output_file_type": "CSV",
                    "types": _IMPORT_SPEC_TEST_DATA,
                },
            )
            js = await resp.json()
            assert js == {
                "output_file_type": "CSV",
                "files_created": {
                    "genome": f"{TEST_USER}/specs/genome.csv",
                    "reads": f"{TEST_USER}/specs/reads.csv",
                },
            }
            base = Path(fu.base_dir) / TEST_USER
            check_file_contents(
                base / "specs/genome.csv",
                [
                    "Data type: genome; Columns: 2; Version: 1\n",
                    "id1,id2\n",
                    "display1,display2\n",
                    "54,boo\n",
                    "32,yikes\n",
                ],
            )
            check_file_contents(
                base / "specs/reads.csv",
                [
                    "Data type: reads; Columns: 2; Version: 1\n",
                    "name,inseam\n",
                    "Reads File Name,Reads inseam measurement in km\n",
                    "myreads.fa,0.1\n",
                ],
            )


async def test_write_bulk_specification_success_tsv():
    # In other tests a username is passed to AppClient but AppClient completely ignores it...
    async with await AppClient.create(config, TEST_TOKEN) as cli:
        with FileUtil() as fu:
            fu.make_dir(TEST_USER)
            types = dict(_IMPORT_SPEC_TEST_DATA)
            types["reads"] = dict(types["reads"])
            types["reads"]["data"] = []
            resp = await cli.post(
                "write_bulk_specification",
                json={
                    "output_directory": "tsvspecs",
                    "output_file_type": "TSV",
                    "types": types,
                },
            )
            js = await resp.json()
            assert js == {
                "output_file_type": "TSV",
                "files_created": {
                    "genome": f"{TEST_USER}/tsvspecs/genome.tsv",
                    "reads": f"{TEST_USER}/tsvspecs/reads.tsv",
                },
            }
            base = Path(fu.base_dir) / TEST_USER
            check_file_contents(
                base / "tsvspecs/genome.tsv",
                [
                    "Data type: genome; Columns: 2; Version: 1\n",
                    "id1\tid2\n",
                    "display1\tdisplay2\n",
                    "54\tboo\n",
                    "32\tyikes\n",
                ],
            )
            check_file_contents(
                base / "tsvspecs/reads.tsv",
                [
                    "Data type: reads; Columns: 2; Version: 1\n",
                    "name\tinseam\n",
                    "Reads File Name\tReads inseam measurement in km\n",
                ],
            )


async def test_write_bulk_specification_success_excel():
    # In other tests a username is passed to AppClient but AppClient completely ignores it...
    async with await AppClient.create(config, TEST_TOKEN) as cli:
        with FileUtil() as fu:
            fu.make_dir(TEST_USER)
            resp = await cli.post(
                "write_bulk_specification/",
                json={
                    "output_directory": "",
                    "output_file_type": "EXCEL",
                    "types": _IMPORT_SPEC_TEST_DATA,
                },
            )
            js = await resp.json()
            assert js == {
                "output_file_type": "EXCEL",
                "files_created": {
                    "genome": f"{TEST_USER}/import_specification.xlsx",
                    "reads": f"{TEST_USER}/import_specification.xlsx",
                },
            }
            wb = openpyxl.load_workbook(Path(fu.base_dir) / TEST_USER / "import_specification.xlsx")
            assert wb.sheetnames == ["genome", "reads"]
            check_excel_contents(
                wb,
                "genome",
                [
                    ["Data type: genome; Columns: 2; Version: 1", None],
                    ["id1", "id2"],
                    ["display1", "display2"],
                    [54, "boo"],
                    [32, "yikes"],
                ],
                [8.0, 8.0],
            )
            check_excel_contents(
                wb,
                "reads",
                [
                    ["Data type: reads; Columns: 2; Version: 1", None],
                    ["name", "inseam"],
                    ["Reads File Name", "Reads inseam measurement in km"],
                    ["myreads.fa", 0.1],
                ],
                [15.0, 30.0],
            )


async def test_write_bulk_specification_fail_wrong_data_type():
    async with await AppClient.create(config, TEST_TOKEN) as cli:
        resp = await cli.post("write_bulk_specification/", data="foo")
        js = await resp.json()
        assert js == {"error": "Required content-type is application/json"}
        assert resp.status == 415


async def test_write_bulk_specification_fail_no_content_length():
    async with await AppClient.create(config, TEST_TOKEN) as cli:
        resp = await cli.post(
            "write_bulk_specification", headers={"content-type": "application/json"}
        )
        js = await resp.json()
        assert js == {"error": "The content-length header is required and must be > 0"}
        assert resp.status == 411


async def test_write_bulk_specification_fail_large_input():
    async with await AppClient.create(config, TEST_TOKEN) as cli:
        resp = await cli.post("write_bulk_specification/", json="a" * (1024 * 1024 - 2))
        txt = await resp.text()
        # this seems to be a built in (somewhat inaccurate) server feature
        assert txt == "Maximum request body size 1048576 exceeded, actual body size 1048576"
        assert resp.status == 413


async def _write_bulk_specification_json_fail(json: Any, err: str):
    async with await AppClient.create(config, TEST_TOKEN) as cli:
        resp = await cli.post("write_bulk_specification", json=json)
        js = await resp.json()
        assert js == {"error": err}
        assert resp.status == 400


async def test_write_bulk_specification_fail_not_dict():
    await _write_bulk_specification_json_fail(
        ["foo"], "The top level JSON element must be a mapping"
    )


async def test_write_bulk_specification_fail_no_output_dir():
    await _write_bulk_specification_json_fail(
        {}, "output_directory is required and must be a string"
    )


async def test_write_bulk_specification_fail_wrong_type_for_output_dir():
    await _write_bulk_specification_json_fail(
        {"output_directory": 4}, "output_directory is required and must be a string"
    )


async def test_write_bulk_specification_fail_no_file_type():
    await _write_bulk_specification_json_fail(
        {"output_directory": "foo"}, "Invalid output_file_type: None"
    )


async def test_write_bulk_specification_fail_wrong_file_type():
    await _write_bulk_specification_json_fail(
        {"output_directory": "foo", "output_file_type": "XSV"},
        "Invalid output_file_type: XSV",
    )


async def test_write_bulk_specification_fail_invalid_type_value():
    await _write_bulk_specification_json_fail(
        {"output_directory": "foo", "output_file_type": "CSV", "types": {"a": "fake"}},
        "The value for data type a must be a mapping",
    )


async def test_importer_filetypes():
    """
    Only checks a few example entries since the list may expand over time
    """
    async with await AppClient.create(config, TEST_TOKEN) as cli:
        resp = await cli.get("importer_filetypes")
        js = await resp.json()
        assert set(js.keys()) == {"datatype_to_filetype", "filetype_to_extensions"}
        a2f = js["datatype_to_filetype"]
        assert a2f["assembly"] == ["FASTA"]
        assert a2f["gff_genome"] == ["FASTA", "GFF"]
        assert a2f["import_specification"] == ["CSV", "EXCEL", "TSV"]
        assert a2f["dts_manifest"] == ["JSON"]

        f2e = js["filetype_to_extensions"]
        assert f2e["FASTA"] == [
            "fa",
            "fa.gz",
            "fa.gzip",
            "faa",
            "faa.gz",
            "faa.gzip",
            "fasta",
            "fasta.gz",
            "fasta.gzip",
            "fna",
            "fna.gz",
            "fna.gzip",
            "fsa",
            "fsa.gz",
            "fsa.gzip",
        ]
        assert f2e["EXCEL"] == ["xls", "xlsx"]
        assert f2e["SRA"] == ["sra"]

        assert resp.status == 200
