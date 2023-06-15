import asyncio
import hashlib
import os
import platform
import shutil
import string
import time
from io import BytesIO
from json import JSONDecoder
from pathlib import Path
from typing import Any
from unittest.mock import patch
from urllib.parse import unquote, urlencode

import openpyxl
import pandas
import pytest
from aiohttp import FormData, test_utils
from hypothesis import given, settings
from hypothesis import strategies as st

import staging_service.app as app
import staging_service.globus as globus
import staging_service.utils as utils
from staging_service.AutoDetectUtils import AutoDetectUtils
from tests.test_helpers import (DATA_DIR, META_DIR, FileUtil,
                                assert_file_contents, bootstrap,
                                check_excel_contents)

if os.environ.get("KB_DEPLOYMENT_CONFIG") is None:
    bootstrap()

decoder = JSONDecoder()


utils.StagingPath._DATA_DIR = DATA_DIR
utils.StagingPath._META_DIR = META_DIR


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


# TODO: replace with real unittest mocking
def mock_app():
    application = app.app_factory()

    async def mock_globus_id(*args, **kwargs):
        return ["testuser@globusid.org"]

    globus._get_globus_ids = (
        mock_globus_id  # TODO this doesn't allow testing of this fn does it
    )
    return application


class AppClient:
    def __init__(self):
        self.server = test_utils.TestServer(mock_app())
        self.client = None

    async def __aenter__(self):
        await self.server.start_server(loop=asyncio.get_event_loop())
        self.client = test_utils.TestClient(self.server, loop=asyncio.get_event_loop())
        return self.client

    async def __aexit__(self, *args):
        await self.server.close()
        if self.client is not None:
            await self.client.close()


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
    assert (
        username + "/foo/bar"
        == utils.StagingPath.validate_path(username, "foo/bar").user_path
    )
    assert (
        username + "/baz"
        == utils.StagingPath.validate_path(username, "foo/../bar/../baz").user_path
    )
    assert (
        username + "/bar"
        == utils.StagingPath.validate_path(username, "foo/../../../../bar").user_path
    )
    assert (
        username + "/foo"
        == utils.StagingPath.validate_path(username, "./foo").user_path
    )
    assert (
        username + "/foo/bar"
        == utils.StagingPath.validate_path(username, "../foo/bar").user_path
    )
    assert (
        username + "/foo"
        == utils.StagingPath.validate_path(username, "/../foo").user_path
    )
    assert (
        username + "/" == utils.StagingPath.validate_path(username, "/foo/..").user_path
    )
    assert (
        username + "/foo"
        == utils.StagingPath.validate_path(username, "/foo/.").user_path
    )
    assert (
        username + "/foo" == utils.StagingPath.validate_path(username, "foo/").user_path
    )
    assert (
        username + "/foo" == utils.StagingPath.validate_path(username, "foo").user_path
    )
    assert (
        username + "/foo"
        == utils.StagingPath.validate_path(username, "/foo/").user_path
    )
    assert (
        username + "/foo" == utils.StagingPath.validate_path(username, "/foo").user_path
    )
    assert (
        username + "/foo"
        == utils.StagingPath.validate_path(username, "foo/.").user_path
    )
    assert username + "/" == utils.StagingPath.validate_path(username, "").user_path
    assert (
        username + "/" == utils.StagingPath.validate_path(username, "foo/..").user_path
    )
    assert (
        username + "/" == utils.StagingPath.validate_path(username, "/..../").user_path
    )
    assert (
        username + "/stuff.ext"
        == utils.StagingPath.validate_path(username, "/stuff.ext").user_path
    )


@given(username_first_strat, username_strat, st.text())
def test_path_sanitation(username_first, username_rest, path):
    username = username_first + username_rest
    validated = utils.StagingPath.validate_path(username, path)
    assert validated.full_path.startswith(DATA_DIR)
    assert validated.user_path.startswith(username)
    assert validated.metadata_path.startswith(META_DIR)
    assert validated.full_path.find("/..") == -1
    assert validated.user_path.find("/..") == -1
    assert validated.metadata_path.find("/..") == -1
    assert validated.full_path.find("../") == -1
    assert validated.user_path.find("../") == -1
    assert validated.metadata_path.find("../") == -1


@asyncgiven(txt=st.text())
async def test_cmd(txt):
    with FileUtil(DATA_DIR) as fs:
        d = fs.make_dir("test")
        assert "" == await utils.run_command("ls", d)
        f = fs.make_file("test/test2", txt)
        md5 = hashlib.md5(txt.encode("utf8")).hexdigest()
        os = platform.system()
        if os == "Linux":
            md52 = await utils.run_command("md5sum", f)
            expected_md5 = md52.split()[0]
        elif os == "Darwin":
            md52 = await utils.run_command("md5", f)
            expected_md5 = md52.split()[3]

        assert md5 == expected_md5

        # For mac osx, copy md5 to md5sum and check 3rd element
        # assert md5 == md52.split()[3]


@pytest.mark.asyncio
@patch("staging_service.auth2Client.KBaseAuth2.get_user")
async def test_auth(get_user):
    get_user.return_value = "testuser"
    async with AppClient() as cli:
        resp = await cli.get("/test-auth")
        assert resp.status == 200
        text = await resp.text()
        assert "I'm authenticated as" in text


@pytest.mark.asyncio
@patch("staging_service.auth2Client.KBaseAuth2.get_user")
async def test_service(get_user):
    get_user.return_value = "testuser"
    async with AppClient() as cli:
        resp = await cli.get("/test-service")
        assert resp.status == 200
        text = await resp.text()
        assert "staging service version" in text


@pytest.mark.asyncio
@patch("staging_service.auth2Client.KBaseAuth2.get_user")
async def test_jgi_metadata(get_user):
    txt = "testing text\n"
    username = "testuser"
    get_user.return_value = username
    jgi_metadata = '{"file_owner": "sdm", "added_date": "2013-08-12T00:21:53.844000"}'

    async with AppClient() as cli:
        with FileUtil() as fs:
            fs.make_dir(os.path.join(username, "test"))
            fs.make_file(os.path.join(username, "test", "test_jgi.fastq"), txt)
            fs.make_file(
                os.path.join(username, "test", ".test_jgi.fastq.jgi"), jgi_metadata
            )
            res1 = await cli.get(
                os.path.join("jgi-metadata", "test", "test_jgi.fastq"),
                headers={"Authorization": ""},
            )
            assert res1.status == 200
            json_text = await res1.text()
            json = decoder.decode(json_text)
            expected_keys = ["file_owner", "added_date"]
            assert set(json.keys()) >= set(expected_keys)
            assert json.get("file_owner") == "sdm"
            assert json.get("added_date") == "2013-08-12T00:21:53.844000"

            # testing non-existing jbi metadata file
            res1 = await cli.get(
                os.path.join("jgi-metadata", "test", "non_existing.1617.2.1467.fastq"),
                headers={"Authorization": ""},
            )
            assert res1.status == 404


@pytest.mark.asyncio
@patch("staging_service.auth2Client.KBaseAuth2.get_user")
async def test_metadata(get_user):
    txt = "testing text\n"
    username = "testuser"
    get_user.return_value = username

    async with AppClient() as cli:
        with FileUtil() as fs:
            fs.make_dir(os.path.join(username, "test"))
            fs.make_file(os.path.join(username, "test", "test_file_1"), txt)
            res1 = await cli.get(
                os.path.join("metadata", "test", "test_file_1"),
                headers={"Authorization": ""},
            )
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
            assert json.get("lineCount") == 1
            assert json.get("head") == "testing text\n"
            assert json.get("tail") == "testing text\n"
            assert json.get("name") == "test_file_1"
            assert json.get("size") == 13
            assert not json.get("isFolder")

            # testing existing metadata file
            res2 = await cli.get(
                os.path.join("metadata", "test", "test_file_1"),
                headers={"Authorization": ""},
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
            assert json.get("lineCount") == 1
            assert json.get("head") == "testing text\n"
            assert json.get("tail") == "testing text\n"
            assert json.get("name") == "test_file_1"
            assert json.get("size") == 13
            assert not json.get("isFolder")

            # testing corrupted metadata file
            path = os.path.join(META_DIR, username, "test", "test_file_1")
            with open(path, encoding="utf-8", mode="w") as f:
                f.write('{"source": "Unknown"}')
            res3 = await cli.get(
                os.path.join("metadata", "test", "test_file_1"),
                headers={"Authorization": ""},
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
            assert json.get("lineCount") == 1
            assert json.get("head") == "testing text\n"
            assert json.get("tail") == "testing text\n"
            assert json.get("name") == "test_file_1"
            assert json.get("size") == 13
            assert not json.get("isFolder")


@pytest.mark.asyncio
@patch("staging_service.auth2Client.KBaseAuth2.get_user")
async def test_define_UPA(get_user):
    txt = "testing text\n"
    username = "testuser"
    get_user.return_value = username

    async with AppClient() as cli:
        with FileUtil() as fs:
            fs.make_dir(os.path.join(username, "test"))
            fs.make_file(os.path.join(username, "test", "test_file_1"), txt)
            # generating metadata file
            res1 = await cli.get(
                os.path.join("metadata", "test", "test_file_1"),
                headers={"Authorization": ""},
            )
            assert res1.status == 200

            # posting UPA
            res2 = await cli.post(
                os.path.join("define-upa", "test", "test_file_1"),
                headers={"Authorization": ""},
                data={"UPA": "test_UPA"},
            )
            assert res2.status == 200
            json_text = await res2.text()
            assert (
                f"successfully updated UPA test_UPA for file {username}/test/test_file_1"
                in json_text
            )

            # getting new metadata
            res3 = await cli.get(
                os.path.join("metadata", "test", "test_file_1"),
                headers={"Authorization": ""},
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
            assert json.get("lineCount") == 1
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
                headers={"Authorization": ""},
                data={"UPA": "test_UPA"},
            )
            assert res4.status == 404

            # testing missing body
            res5 = await cli.post(
                os.path.join("define-upa", "test", "test_file_1"),
                headers={"Authorization": ""},
            )
            assert res5.status == 400

            # testing missing UPA in body
            res6 = await cli.post(
                os.path.join("define-upa", "test", "test_file_1"),
                headers={"Authorization": ""},
                data={"missing_UPA": "test_UPA"},
            )
            assert res6.status == 400


@pytest.mark.asyncio
@patch("staging_service.auth2Client.KBaseAuth2.get_user")
async def test_mv(get_user):
    txt = "testing text\n"
    username = "testuser"
    get_user.return_value = username
    async with AppClient() as cli:
        with FileUtil() as fs:
            fs.make_dir(os.path.join(username, "test"))
            fs.make_file(os.path.join(username, "test", "test_file_1"), txt)

            # list current test directory
            res1 = await cli.get(
                os.path.join("list", "test"), headers={"Authorization": ""}
            )
            assert res1.status == 200
            json_text = await res1.text()
            json = decoder.decode(json_text)
            assert len(json) == 1
            assert json[0]["name"] == "test_file_1"

            res2 = await cli.patch(
                os.path.join("mv", "test", "test_file_1"),
                headers={"Authorization": ""},
                data={"newPath": "test/test_file_2"},
            )
            assert res2.status == 200
            json_text = await res2.text()
            assert "successfully moved" in json_text

            # relist test directory
            res3 = await cli.get(
                os.path.join("list", "test"), headers={"Authorization": ""}
            )
            assert res3.status == 200
            json_text = await res3.text()
            json = decoder.decode(json_text)
            assert len(json) == 1
            assert json[0]["name"] == "test_file_2"

            # testing moving root
            # res4 = await cli.patch('/mv',
            #                        headers={'Authorization': ''},
            #                        data={'newPath': 'test/test_file_2'})
            # assert res4.status == 403

            # testing missing body
            res5 = await cli.patch(
                os.path.join("mv", "test", "test_file_1"), headers={"Authorization": ""}
            )
            assert res5.status == 400

            # testing missing newPath in body
            res6 = await cli.patch(
                os.path.join("mv", "test", "test_file_1"),
                headers={"Authorization": ""},
                data={"missing_newPath": "test/test_file_2"},
            )
            assert res6.status == 400

            # testing moving to existing file
            res7 = await cli.patch(
                os.path.join("mv", "test", "test_file_2"),
                headers={"Authorization": ""},
                data={"newPath": "test/test_file_2"},
            )
            assert res7.status == 409

            # testing non-existing file
            res7 = await cli.patch(
                os.path.join("mv", "test", "non_existing.test_file_2"),
                headers={"Authorization": ""},
                data={"newPath": "test/test_file_2"},
            )
            assert res7.status == 404


@pytest.mark.asyncio
@patch("staging_service.auth2Client.KBaseAuth2.get_user")
async def test_delete(get_user):
    txt = "testing text\n"
    username = "testuser"
    get_user.return_value = username
    with patch("staging_service.auth2Client.KBaseAuth2") as mock_auth:
        mock_auth.return_value.get_user.return_value = username
        async with AppClient() as cli:
            with FileUtil() as fs:
                fs.make_dir(os.path.join(username, "test"))
                fs.make_file(os.path.join(username, "test", "test_file_1"), txt)

                # list current test directory
                res1 = await cli.get(
                    os.path.join("list", "test"), headers={"Authorization": ""}
                )
                assert res1.status == 200
                json_text = await res1.text()
                json = decoder.decode(json_text)
                assert len(json) == 1
                assert json[0]["name"] == "test_file_1"

                res2 = await cli.delete(
                    os.path.join("delete", "test", "test_file_1"),
                    headers={"Authorization": ""},
                )
                assert res2.status == 200
                json_text = await res2.text()
                assert "successfully deleted" in json_text

                # relist test directory
                res3 = await cli.get(
                    os.path.join("list", "test"), headers={"Authorization": ""}
                )
                assert res3.status == 200
                json_text = await res3.text()
                json = decoder.decode(json_text)
                assert len(json) == 0

                # testing moving root
                # res4 = await cli.delete('/delete/',
                #                         headers={'Authorization': ''})
                # assert res4.status == 403

                # testing non-existing file
                res5 = await cli.delete(
                    os.path.join("delete", "test", "non_existing.test_file_2"),
                    headers={"Authorization": ""},
                )
                assert res5.status == 404


@pytest.mark.asyncio
@patch("staging_service.auth2Client.KBaseAuth2.get_user")
async def test_list(get_user):
    txt = "testing text"
    username = "testuser"
    get_user.return_value = username
    async with AppClient() as cli:
        with FileUtil() as fs:
            fs.make_dir(os.path.join(username, "test"))
            fs.make_file(os.path.join(username, "test", "test_file_1"), txt)
            fs.make_dir(os.path.join(username, "test", "test_sub_dir"))
            fs.make_file(
                os.path.join(username, "test", "test_sub_dir", "test_file_2"), txt
            )
            res1 = await cli.get("list/..", headers={"Authorization": ""})
            assert res1.status == 404
            res2 = await cli.get(
                os.path.join("list", "test", "test_file_1"),
                headers={"Authorization": ""},
            )
            assert res2.status == 400

            # testing root directory with 'list/' routes
            res3 = await cli.get("/list/", headers={"Authorization": ""})
            assert res3.status == 200
            json_text = await res3.text()
            json = decoder.decode(json_text)
            file_folder_count = [file_json["isFolder"] for file_json in json]
            assert json[0]["isFolder"] is True
            assert json[0]["name"] == "test"
            assert json[0]["path"] == "testuser/test"
            assert json[0]["mtime"] <= time.time() * 1000
            assert len(file_folder_count) == 4  # 2 folders and 2 files
            assert sum(file_folder_count) == 2

            # testing root directory with 'list' route
            res4 = await cli.get("/list", headers={"Authorization": ""})
            assert res4.status == 200
            json_text = await res4.text()
            json = decoder.decode(json_text)
            file_folder_count = [file_json["isFolder"] for file_json in json]
            assert json[0]["isFolder"] is True
            assert json[0]["name"] == "test"
            assert json[0]["path"] == "testuser/test"
            assert json[0]["mtime"] <= time.time() * 1000
            assert len(file_folder_count) == 4  # 2 folders and 2 files
            assert sum(file_folder_count) == 2

            # testing sub-directory
            res5 = await cli.get(
                os.path.join("list", "test"), headers={"Authorization": ""}
            )
            assert res5.status == 200
            json_text = await res5.text()
            json = decoder.decode(json_text)
            file_folder_count = [file_json["isFolder"] for file_json in json]
            # 1 sub-directory, 1 file in sub-directory and 1 file in root
            assert len(file_folder_count) == 3
            assert sum(file_folder_count) == 1

            # testing list dot-files
            fs.make_file(os.path.join(username, "test", ".test_file_1"), txt)
            # f5 = fs.make_file(os.path.join(username, 'test', '.globus_id'), txt)
            res6 = await cli.get("/list/", headers={"Authorization": ""})
            assert res6.status == 200
            json_text = await res6.text()
            json = decoder.decode(json_text)

            file_names = [
                file_json["name"] for file_json in json if not file_json["isFolder"]
            ]
            assert ".test_file_1" not in file_names
            assert ".globus_id" not in file_names
            assert len(file_names) == 2

            # testing list showHidden option
            res7 = await cli.get(
                "/list/", headers={"Authorization": ""}, params={"showHidden": "True"}
            )
            assert res7.status == 200
            json_text = await res7.text()
            json = decoder.decode(json_text)
            file_names = [
                file_json["name"] for file_json in json if not file_json["isFolder"]
            ]
            assert ".test_file_1" in file_names
            assert ".globus_id" in file_names
            assert len(file_names) == 4


@patch("staging_service.auth2Client.KBaseAuth2.get_user")
@asyncgiven(txt=st.text())
@pytest.mark.asyncio
async def test_download(get_user, txt):
    username = "testuser"
    get_user.return_value = username
    async with AppClient() as cli:
        with FileUtil() as fs:
            fs.make_dir(os.path.join(username, "test"))
            fs.make_file(os.path.join(username, "test", "test_file_1"), txt)

            res = await cli.get(
                os.path.join("download", "test", "test_file_1"),
                headers={"Authorization": ""},
            )
            assert res.status == 200
            result_text = await res.read()
            assert result_text == txt.encode()


@pytest.mark.asyncio
@patch("staging_service.auth2Client.KBaseAuth2.get_user")
async def test_download_errors(get_user):
    username = "testuser"
    get_user.return_value = username
    async with AppClient() as cli:
        with FileUtil() as fs:
            fs.make_dir(os.path.join(username, "test"))

            res1 = await cli.get("dwnload", headers={"Authorization": ""})
            assert res1.status == 404
            res2 = await cli.get(
                os.path.join("download", "test", ""), headers={"Authorization": ""}
            )
            assert res2.status == 400


@pytest.mark.asyncio
@patch("staging_service.auth2Client.KBaseAuth2.get_user")
async def test_similar(get_user):
    txt = "testing text"
    username = "testuser"
    get_user.return_value = username
    async with AppClient() as cli:
        with FileUtil() as fs:
            fs.make_dir(os.path.join(username, "test"))
            fs.make_file(os.path.join(username, "test", "test_file_1.fq"), txt)
            fs.make_dir(os.path.join(username, "test", "test_sub_dir"))
            fs.make_file(
                os.path.join(username, "test", "test_sub_dir", "test_file_2.fq"), txt
            )
            fs.make_file(
                os.path.join(username, "test", "test_sub_dir", "test_file_right.fq"),
                txt,
            )
            fs.make_file(
                os.path.join(username, "test", "test_sub_dir", "my_files"), txt
            )

            # testing similar file name
            res1 = await cli.get(
                "similar/test/test_file_1.fq", headers={"Authorization": ""}
            )
            assert res1.status == 200
            json_text = await res1.text()
            json = decoder.decode(json_text)
            assert len(json) == 2
            assert json[0].get("name") in ["test_file_2.fq", "test_file_right.fq"]
            assert json[1].get("name") in ["test_file_2.fq", "test_file_right.fq"]

            # testing non-existing file
            res2 = await cli.get(
                "similar/test/non-existing", headers={"Authorization": ""}
            )
            assert res2.status == 404

            # testing path is a directory
            res3 = await cli.get("similar/test", headers={"Authorization": ""})
            assert res3.status == 400


@pytest.mark.asyncio
@patch("staging_service.auth2Client.KBaseAuth2.get_user")
async def test_existence(get_user):
    txt = "testing text"
    username = "testuser"
    get_user.return_value = username
    async with AppClient() as cli:
        with FileUtil() as fs:
            fs.make_dir(os.path.join(username, "test"))
            fs.make_file(os.path.join(username, "test", "test_file_1"), txt)
            fs.make_dir(os.path.join(username, "test", "test_sub_dir"))
            fs.make_file(
                os.path.join(username, "test", "test_sub_dir", "test_file_2"), txt
            )
            fs.make_dir(os.path.join(username, "test", "test_sub_dir", "test_file_1"))
            fs.make_dir(os.path.join(username, "test", "test_sub_dir", "test_sub_dir"))
            fs.make_file(
                os.path.join(
                    username, "test", "test_sub_dir", "test_sub_dir", "test_file_1"
                ),
                txt,
            )

            # testing existence of both file and folder name
            res1 = await cli.get("existence/test_file_1", headers={"Authorization": ""})
            assert res1.status == 200
            json_text = await res1.text()
            json = decoder.decode(json_text)
            assert json["exists"] is True
            assert json["isFolder"] is False

            # testing existence of file
            res2 = await cli.get("existence/test_file_2", headers={"Authorization": ""})
            assert res2.status == 200
            json_text = await res2.text()
            json = decoder.decode(json_text)
            assert json["exists"] is True
            assert json["isFolder"] is False

            # testing existence of folder
            res3 = await cli.get(
                "existence/test_sub_dir", headers={"Authorization": ""}
            )
            assert res3.status == 200
            json_text = await res3.text()
            json = decoder.decode(json_text)
            assert json["exists"] is True
            assert json["isFolder"] is True

            # testing non-existence
            res4 = await cli.get("existence/fake_file", headers={"Authorization": ""})
            assert res4.status == 200
            json_text = await res4.text()
            json = decoder.decode(json_text)
            assert json["exists"] is False
            assert json["isFolder"] is False

            res5 = await cli.get("existence/test_sub", headers={"Authorization": ""})
            assert res5.status == 200
            json_text = await res5.text()
            json = decoder.decode(json_text)
            assert json["exists"] is False
            assert json["isFolder"] is False


@pytest.mark.asyncio
@patch("staging_service.auth2Client.KBaseAuth2.get_user")
async def test_search(get_user):
    txt = "testing text"
    username = "testuser"
    get_user.return_value = username
    async with AppClient() as cli:
        with FileUtil() as fs:
            fs.make_dir(os.path.join(username, "test"))
            fs.make_file(os.path.join(username, "test", "test1"), txt)
            fs.make_dir(os.path.join(username, "test", "test2"))
            fs.make_file(os.path.join(username, "test", "test2", "test3"), txt)
            res1 = await cli.get("search/", headers={"Authorization": ""})
            assert res1.status == 200
            json_text = await res1.text()
            json = decoder.decode(json_text)
            assert len(json) == 4
            res2 = await cli.get("search/test1", headers={"Authorization": ""})
            assert res2.status == 200
            json_text = await res2.text()
            json = decoder.decode(json_text)
            assert len(json) == 1
            res3 = await cli.get("search/test2", headers={"Authorization": ""})
            assert res3.status == 200
            json_text = await res3.text()
            json = decoder.decode(json_text)
            assert len(json) == 2


@pytest.mark.asyncio
@patch("staging_service.auth2Client.KBaseAuth2.get_user")
async def test_upload(get_user):
    txt = "testing text\n"
    username = "testuser"
    get_user.return_value = username
    async with AppClient() as cli:
        # testing missing body
        res1 = await cli.post("upload", headers={"Authorization": ""})
        assert res1.status == 400

        with FileUtil() as fs:
            fs.make_dir(os.path.join(username, "test"))
            f = fs.make_file(os.path.join(username, "test", "test_file_1"), txt)

            files = {"destPath": "/", "uploads": open(f, "rb")}

            res2 = await cli.post(
                os.path.join("upload"), headers={"Authorization": ""}, data=files
            )

            assert res2.status == 200


async def _upload_file_fail_filename(filename: str, err: str):
    # Note two file uploads in a row causes a test error:
    # https://github.com/aio-libs/aiohttp/issues/3968
    async with AppClient() as cli:
        formdata = FormData()
        formdata.add_field("destPath", "/")
        formdata.add_field("uploads", BytesIO(b"sometext"), filename=filename)

        res = await cli.post("upload", headers={"Authorization": ""}, data=formdata)

        assert await res.text() == err
        assert res.status == 403


@pytest.mark.asyncio
@patch("staging_service.auth2Client.KBaseAuth2.get_user")
async def test_upload_fail_leading_space(get_user):
    get_user.return_value = "fake"
    await _upload_file_fail_filename(
        " test_file", "cannot upload file with name beginning with space"
    )


@pytest.mark.asyncio
@patch("staging_service.auth2Client.KBaseAuth2.get_user")
async def test_upload_fail_dotfile(get_user):
    get_user.return_value = "whocares"
    await _upload_file_fail_filename(
        ".test_file", "cannot upload file with name beginning with '.'"
    )


@pytest.mark.asyncio
@patch("staging_service.auth2Client.KBaseAuth2.get_user")
async def test_upload_fail_comma_in_file(get_user):
    get_user.return_value = "idunno"
    await _upload_file_fail_filename("test,file", "cannot upload file with ',' in name")


@patch("staging_service.auth2Client.KBaseAuth2.get_user")
@settings(deadline=None)
@asyncgiven(contents=st.text())
@pytest.mark.asyncio
async def test_directory_decompression(get_user, contents):
    fname = "test"
    dirname = "dirname"
    username = "testuser"
    get_user.return_value = username
    path = utils.StagingPath.validate_path(username, os.path.join(dirname, fname))
    path2 = utils.StagingPath.validate_path(username, os.path.join(dirname, fname))
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
    async with AppClient() as cli:
        for method, extension in methods:
            with FileUtil() as fs:
                d = fs.make_dir(os.path.join(username, dirname))
                f1 = fs.make_file(path.user_path, contents)
                d2 = fs.make_dir(os.path.join(username, dirname, dirname))
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
                resp = await cli.patch(
                    "/decompress/" + name, headers={"Authorization": ""}
                )
                assert resp.status == 200
                text = await resp.text()
                assert "succesfully decompressed" in text
                assert name in text
                # check to see if we got back what we started with for all files and directories
                assert os.path.exists(d)
                assert os.path.exists(d)
                assert os.path.exists(f1)
                assert os.path.exists(d2)
                assert os.path.exists(f3)


@patch("staging_service.auth2Client.KBaseAuth2.get_user")
@asyncgiven(contents=st.text())
@pytest.mark.asyncio
async def test_file_decompression(get_user, contents):
    fname = "test"
    dirname = "dirname"
    username = "testuser"
    get_user.return_value = username
    path = utils.StagingPath.validate_path(username, os.path.join(dirname, fname))
    if path.user_path.endswith("/"):
        # invalid test case
        # TODO it should be faster if hypothesis could generate all cases except these
        return
    methods = [("gzip", ".gz"), ("bzip2", ".bz2")]
    with patch("staging_service.auth2Client.KBaseAuth2") as mock_auth:
        mock_auth.return_value.get_user.return_value = username
        async with AppClient() as cli:
            for method, extension in methods:
                with FileUtil() as fs:
                    d = fs.make_dir(os.path.join(username, dirname))
                    f1 = fs.make_file(path.user_path, contents)
                    name = fname + extension
                    await utils.run_command(method, f1)
                    # check to see that the original is gone
                    assert os.path.exists(d)
                    assert not os.path.exists(f1)
                    assert os.path.exists(os.path.join(d, name))
                    resp = await cli.patch(
                        "/decompress/" + os.path.join(dirname, name),
                        headers={"Authorization": ""},
                    )
                    assert resp.status == 200
                    text = await resp.text()
                    assert "succesfully decompressed" in text
                    assert name in text
                    # check to see if we got back what we started with for all files and directories
                    assert os.path.exists(d)
                    assert os.path.exists(f1)


@pytest.mark.asyncio
@patch("staging_service.auth2Client.KBaseAuth2.get_user")
async def test_importer_mappings(get_user):
    """
    This tests calling with simple good cases, and some expected bad cases
    :return:
    """
    username = "testuser"
    get_user.return_value = username

    # Normal case, no match
    data = {"file_list": ["file1.txt"]}
    qs1 = urlencode(data, doseq=True)

    async with AppClient() as cli:
        resp = await cli.get(f"importer_mappings/?{qs1}")
        assert resp.status == 200
        text = await resp.json()
        assert "mappings" in text
        mappings = text["mappings"]
        assert mappings[0] is None

    # Normal case, one match
    data = {"file_list": ["file1.txt", "file.tar.gz"]}
    qs2 = urlencode(data, doseq=True)

    async with AppClient() as cli:
        resp = await cli.get(f"importer_mappings/?{qs2}", data=data)
        assert resp.status == 200
        text = await resp.json()
        assert "mappings" in text
        mappings = text["mappings"]
        assert mappings[0] is None
        # As we update the app mappings this test may need to be changed
        # Or we need to reload json file itself

        # unzip_mapping = AutoDetectUtils._MAPPINGS["apps"]["decompress/unpack"]
        assert (
            mappings[1][0]
            == AutoDetectUtils.get_mappings_by_extension("gz")["mappings"][0]
        )

    # A dict is passed in
    data = {"file_list": [{}]}
    qs3 = urlencode(data, doseq=True)

    async with AppClient() as cli:
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

        async with AppClient() as cli:
            resp = await cli.get(f"importer_mappings/?{qsd}")
            assert resp.status == 400
            text = await resp.text()
            assert (
                f"must provide file_list field. Your provided qs: {unquote(qsd)}"
                in text
            )


@pytest.mark.asyncio
@patch("staging_service.auth2Client.KBaseAuth2.get_user")
async def test_bulk_specification_success(get_user):
    username = "testuser"
    get_user.return_value = username

    async with AppClient() as cli:
        with FileUtil() as fu:
            fu.make_dir(f"{username}/somefolder")
            base = Path(fu.base_dir) / username
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

            resp = await cli.get(
                f"bulk_specification/?files={tsv}  ,   {csv},  {excel}   "
            )
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
                    "tree_sloths": [
                        {"entity_id": "That which ends all", "preferred_food": "ꔆ"}
                    ],
                },
                "files": {
                    "genomes": {"file": "testuser/genomes.tsv", "tab": None},
                    "breakfastcereals": {
                        "file": "testuser/somefolder/breakfastcereals.csv",
                        "tab": None,
                    },
                    "fruit_bats": {"file": "testuser/importspec.xlsx", "tab": "bats"},
                    "tree_sloths": {
                        "file": "testuser/importspec.xlsx",
                        "tab": "sloths",
                    },
                },
            }
            assert resp.status == 200


@pytest.mark.asyncio
@patch("staging_service.auth2Client.KBaseAuth2.get_user")
async def test_bulk_specification_fail_no_files(get_user):
    get_user.return_value = "dontcare"
    async with AppClient() as cli:
        for f in ["", "?files=", "?files=  ,   ,,   ,  "]:
            resp = await cli.get(f"bulk_specification/{f}")
            jsn = await resp.json()
            assert jsn == {"errors": [{"type": "no_files_provided"}]}
            assert resp.status == 400


@pytest.mark.asyncio
@patch("staging_service.auth2Client.KBaseAuth2.get_user")
async def test_bulk_specification_fail_not_found(get_user):
    username = "testuser"
    get_user.return_value = username
    async with AppClient() as cli:
        with FileUtil() as fu:
            fu.make_dir(f"{username}/otherfolder")
            base = Path(fu.base_dir) / username
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
                "errors": [
                    {"type": "cannot_find_file", "file": f"{username}/somefile.csv"}
                ]
            }
            assert resp.status == 404


@pytest.mark.asyncio
@patch("staging_service.auth2Client.KBaseAuth2.get_user")
async def test_bulk_specification_fail_parse_fail(get_user):
    """
    Tests a number of different parse fail cases, including incorrect file types.
    Also tests that all the errors are combined correctly.
    """
    username = "testuser"
    get_user.return_value = username
    async with AppClient() as cli:
        with FileUtil() as fu:
            fu.make_dir(f"{username}/otherfolder")
            base = Path(fu.base_dir) / username
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
                        "file": f"{username}/otherfolder/thing.csv",
                        "tab": None,
                    },
                    {
                        "type": "cannot_parse_file",
                        "message": "Missing header entry in row 2, position 1",
                        "file": f"{username}/stuff.xlsx",
                        "tab": "sloths",
                    },
                    {
                        "type": "cannot_parse_file",
                        "message": "badfile is not a supported file type for import specifications",
                        "file": f"{username}/badfile",
                        "tab": None,
                    },
                    {
                        "type": "cannot_parse_file",
                        "message": "fasta.gz is not a supported file type for import specifications",
                        "file": f"{username}/badfile.fasta.gz",
                        "tab": None,
                    },
                    {
                        "type": "cannot_parse_file",
                        "message": "sra is not a supported file type for import specifications",
                        "file": f"{username}/badfile.sra",
                        "tab": None,
                    },
                    {
                        "type": "cannot_parse_file",
                        "message": "sys is not a supported file type for import specifications",
                        "file": f"{username}/badfile.sys",
                        "tab": None,
                    },
                    {
                        "type": "cannot_parse_file",
                        "message": "badfile. is not a supported file type for import specifications",
                        "file": f"{username}/badfile.",
                        "tab": None,
                    },
                ]
            }
            assert resp.status == 400


@pytest.mark.asyncio
@patch("staging_service.auth2Client.KBaseAuth2.get_user")
async def test_bulk_specification_fail_column_count(get_user):
    username = "testuser"
    get_user.return_value = username
    async with AppClient() as cli:
        with FileUtil() as fu:
            fu.make_dir(username)
            base = Path(fu.base_dir) / username
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
                        "file": f"{username}/thing.csv",
                        "tab": None,
                    },
                    {
                        "type": "incorrect_column_count",
                        "message": "Incorrect number of items in line 4, expected 2, got 3",
                        "file": f"{username}/stuff.xlsx",
                        "tab": "bats",
                    },
                ]
            }
            assert resp.status == 400


@pytest.mark.asyncio
@patch("staging_service.auth2Client.KBaseAuth2.get_user")
async def test_bulk_specification_fail_multiple_specs_per_type(get_user):
    username = "testuser"
    get_user.return_value = username
    async with AppClient() as cli:
        with FileUtil() as fu:
            fu.make_dir(username)
            base = Path(fu.base_dir) / username
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

            resp = await cli.get(
                f"bulk_specification/?files={tsv},{csv1},{csv2},{excel}"
            )
            jsn = await resp.json()
            err = "Data type breakfastcereals appears in two importer specification sources"
            assert jsn == {
                "errors": [
                    {
                        "type": "multiple_specifications_for_data_type",
                        "message": err,
                        "file_1": f"{username}/thing.csv",
                        "tab_1": None,
                        "file_2": f"{username}/thing2.csv",
                        "tab_2": None,
                    },
                    {
                        "type": "multiple_specifications_for_data_type",
                        "message": err,
                        "file_1": f"{username}/thing.csv",
                        "tab_1": None,
                        "file_2": f"{username}/stuff.xlsx",
                        "tab_2": "bats",
                    },
                ]
            }
            assert resp.status == 400


@pytest.mark.asyncio
@patch("staging_service.auth2Client.KBaseAuth2.get_user")
async def test_bulk_specification_fail_multiple_specs_per_type_excel(get_user):
    """
    Test an excel file with an internal data type collision.
    This is the only case when all 5 error fields are filled out.
    """
    username = "testuser"
    get_user.return_value = username
    async with AppClient() as cli:
        with FileUtil() as fu:
            fu.make_dir(username)
            base = Path(fu.base_dir) / username
            excel = "stuff.xlsx"
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
                        "file_1": f"{username}/stuff.xlsx",
                        "tab_1": "bats",
                        "file_2": f"{username}/stuff.xlsx",
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


@pytest.mark.asyncio
@patch("staging_service.auth2Client.KBaseAuth2.get_user")
async def test_write_bulk_specification_success_csv(get_user):
    # In other tests a username is passed to AppClient but AppClient completely ignores it...
    username = "testuser"
    get_user.return_value = username
    async with AppClient() as cli:
        with FileUtil() as fu:
            fu.make_dir(username)
            resp = await cli.post(
                "write_bulk_specification/",
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
                    "genome": f"{username}/specs/genome.csv",
                    "reads": f"{username}/specs/reads.csv",
                },
            }
            base = Path(fu.base_dir) / username
            assert_file_contents(
                base / "specs/genome.csv",
                [
                    "Data type: genome; Columns: 2; Version: 1\n",
                    "id1,id2\n",
                    "display1,display2\n",
                    "54,boo\n",
                    "32,yikes\n",
                ],
            )
            assert_file_contents(
                base / "specs/reads.csv",
                [
                    "Data type: reads; Columns: 2; Version: 1\n",
                    "name,inseam\n",
                    "Reads File Name,Reads inseam measurement in km\n",
                    "myreads.fa,0.1\n",
                ],
            )


@pytest.mark.asyncio
@patch("staging_service.auth2Client.KBaseAuth2.get_user")
async def test_write_bulk_specification_success_tsv(get_user):
    # In other tests a username is passed to AppClient but AppClient completely ignores it...
    username = "foo"
    get_user.return_value = username
    async with AppClient() as cli:
        with FileUtil() as fu:
            fu.make_dir(username)
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
                    "genome": f"{username}/tsvspecs/genome.tsv",
                    "reads": f"{username}/tsvspecs/reads.tsv",
                },
            }
            base = Path(fu.base_dir) / username
            assert_file_contents(
                base / "tsvspecs/genome.tsv",
                [
                    "Data type: genome; Columns: 2; Version: 1\n",
                    "id1\tid2\n",
                    "display1\tdisplay2\n",
                    "54\tboo\n",
                    "32\tyikes\n",
                ],
            )
            assert_file_contents(
                base / "tsvspecs/reads.tsv",
                [
                    "Data type: reads; Columns: 2; Version: 1\n",
                    "name\tinseam\n",
                    "Reads File Name\tReads inseam measurement in km\n",
                ],
            )


@pytest.mark.asyncio
@patch("staging_service.auth2Client.KBaseAuth2.get_user")
async def test_write_bulk_specification_success_excel(get_user):
    username = "leaf"
    get_user.return_value = username
    async with AppClient() as cli:
        with FileUtil() as fu:
            fu.make_dir(username)
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
                    "genome": f"{username}/import_specification.xlsx",
                    "reads": f"{username}/import_specification.xlsx",
                },
            }
            wb = openpyxl.load_workbook(
                Path(fu.base_dir) / f"{username}/import_specification.xlsx"
            )
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


@pytest.mark.asyncio
@patch("staging_service.auth2Client.KBaseAuth2.get_user")
async def test_write_bulk_specification_fail_wrong_data_type(get_user):
    get_user.return_value = "dontcare"
    async with AppClient() as cli:
        resp = await cli.post("write_bulk_specification/", data="foo")
        js = await resp.json()
        assert js == {"error": "Required content-type is application/json"}
        assert resp.status == 415


@pytest.mark.asyncio
@patch("staging_service.auth2Client.KBaseAuth2.get_user")
async def test_write_bulk_specification_fail_no_content_length(get_user):
    get_user.return_value = "whocares"
    async with AppClient() as cli:
        resp = await cli.post(
            "write_bulk_specification", headers={"content-type": "application/json"}
        )
        js = await resp.json()
        assert js == {"error": "The content-length header is required and must be > 0"}
        assert resp.status == 411


@pytest.mark.asyncio
@patch("staging_service.auth2Client.KBaseAuth2.get_user")
async def test_write_bulk_specification_fail_large_input(get_user):
    get_user.return_value = "idont"
    async with AppClient() as cli:
        resp = await cli.post("write_bulk_specification/", json="a" * (1024 * 1024 - 2))
        txt = await resp.text()
        # this seems to be a built in (somewhat inaccurate) server feature
        assert (
            txt
            == "Maximum request body size 1048576 exceeded, actual body size 1048576"
        )
        assert resp.status == 413


async def _write_bulk_specification_json_fail(json: Any, err: str):
    async with AppClient() as cli:
        resp = await cli.post("write_bulk_specification", json=json)
        js = await resp.json()
        assert js == {"error": err}
        assert resp.status == 400


@pytest.mark.asyncio
@patch("staging_service.auth2Client.KBaseAuth2.get_user")
async def test_write_bulk_specification_fail_not_dict(get_user):
    get_user.return_value = "dontcare"
    await _write_bulk_specification_json_fail(
        ["foo"], "The top level JSON element must be a mapping"
    )


@pytest.mark.asyncio
@patch("staging_service.auth2Client.KBaseAuth2.get_user")
async def test_write_bulk_specification_fail_no_output_dir(get_user):
    get_user.return_value = "dontcare"
    await _write_bulk_specification_json_fail(
        {}, "output_directory is required and must be a string"
    )


@pytest.mark.asyncio
@patch("staging_service.auth2Client.KBaseAuth2.get_user")
async def test_write_bulk_specification_fail_wrong_type_for_output_dir(get_user):
    get_user.return_value = "dontcare"
    await _write_bulk_specification_json_fail(
        {"output_directory": 4}, "output_directory is required and must be a string"
    )


@pytest.mark.asyncio
@patch("staging_service.auth2Client.KBaseAuth2.get_user")
async def test_write_bulk_specification_fail_no_file_type(get_user):
    get_user.return_value = "dontcare"
    await _write_bulk_specification_json_fail(
        {"output_directory": "foo"}, "Invalid output_file_type: None"
    )


@pytest.mark.asyncio
@patch("staging_service.auth2Client.KBaseAuth2.get_user")
async def test_write_bulk_specification_fail_wrong_file_type(get_user):
    get_user.return_value = "dontcare"
    await _write_bulk_specification_json_fail(
        {"output_directory": "foo", "output_file_type": "XSV"},
        "Invalid output_file_type: XSV",
    )


@pytest.mark.asyncio
@patch("staging_service.auth2Client.KBaseAuth2.get_user")
async def test_write_bulk_specification_fail_invalid_type_value(get_user):
    get_user.return_value = "dontcare"
    await _write_bulk_specification_json_fail(
        {"output_directory": "foo", "output_file_type": "CSV", "types": {"a": "fake"}},
        "The value for data type a must be a mapping",
    )


@pytest.mark.asyncio
@patch("staging_service.auth2Client.KBaseAuth2.get_user")
async def test_importer_filetypes(get_user):
    """
    Only checks a few example entries since the list may expand over time
    """
    get_user.return_value = "dontcare"
    async with AppClient() as cli:
        resp = await cli.get("importer_filetypes")
        js = await resp.json()
        assert set(js.keys()) == {"datatype_to_filetype", "filetype_to_extensions"}
        a2f = js["datatype_to_filetype"]
        assert a2f["assembly"] == ["FASTA"]
        assert a2f["gff_genome"] == ["FASTA", "GFF"]
        assert a2f["import_specification"] == ["CSV", "EXCEL", "TSV"]

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
