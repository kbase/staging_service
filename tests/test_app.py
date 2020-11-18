import asyncio
import configparser
import hashlib
import os
import shutil
import string
import time
from json import JSONDecoder
from urllib.parse import urlencode

from aiohttp import test_utils
from hypothesis import given, settings
from hypothesis import strategies as st

import staging_service.app as app
import staging_service.globus as globus
import staging_service.utils as utils
from staging_service.AutoDetectUtils import AutoDetectUtils

if os.environ.get("KB_DEPLOYMENT_CONFIG") is None:
    from tests.test_utils import bootstrap

    bootstrap()

decoder = JSONDecoder()

config = configparser.ConfigParser()
config.read(os.environ["KB_DEPLOYMENT_CONFIG"])

DATA_DIR = config["staging_service"]["DATA_DIR"]
META_DIR = config["staging_service"]["META_DIR"]
AUTH_URL = config["staging_service"]["AUTH_URL"]
if DATA_DIR.startswith("."):
    DATA_DIR = os.path.normpath(os.path.join(os.getcwd(), DATA_DIR))
if META_DIR.startswith("."):
    META_DIR = os.path.normpath(os.path.join(os.getcwd(), META_DIR))
utils.Path._DATA_DIR = DATA_DIR
utils.Path._META_DIR = META_DIR


def asyncgiven(**kwargs):
    """alterantive to hypothesis.given decorator for async"""

    def real_decorator(fn):
        @given(**kwargs)
        def aio_wrapper(*args, **kwargs):
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            future = asyncio.wait_for(fn(*args, **kwargs), timeout=60)
            loop.run_until_complete(future)

        return aio_wrapper

    return real_decorator


def mock_auth_app():
    application = app.app_factory(config)

    async def mock_auth(*args, **kwargs):
        return "testuser"

    app.auth_client.get_user = mock_auth

    async def mock_globus_id(*args, **kwargs):
        return ["testuser@globusid.org"]

    globus._get_globus_ids = (
        mock_globus_id  # TODO this doesn't allow testing of this fn does it
    )
    return application


class AppClient:
    def __init__(self, config, mock_username=None):
        self.server = test_utils.TestServer(mock_auth_app())

    async def __aenter__(self):
        await self.server.start_server(loop=asyncio.get_event_loop())
        self.client = test_utils.TestClient(self.server, loop=asyncio.get_event_loop())
        return self.client

    async def __aexit__(self, *args):
        await self.server.close()
        await self.client.close()


class FileUtil:
    def __init__(self, base_dir=DATA_DIR):
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
    assert (
            username + "/foo/bar" == utils.Path.validate_path(username, "foo/bar").user_path
    )
    assert (
            username + "/baz"
            == utils.Path.validate_path(username, "foo/../bar/../baz").user_path
    )
    assert (
            username + "/bar"
            == utils.Path.validate_path(username, "foo/../../../../bar").user_path
    )
    assert username + "/foo" == utils.Path.validate_path(username, "./foo").user_path
    assert (
            username + "/foo/bar"
            == utils.Path.validate_path(username, "../foo/bar").user_path
    )
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
    assert (
            username + "/stuff.ext"
            == utils.Path.validate_path(username, "/stuff.ext").user_path
    )


@given(username_first_strat, username_strat, st.text())
def test_path_sanitation(username_first, username_rest, path):
    username = username_first + username_rest
    validated = utils.Path.validate_path(username, path)
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
        md52 = await utils.run_command("md5sum", f)
        assert md5 == md52.split()[0]

        # For mac osx, copy md5 to md5sum and check 3rd element
        # assert md5 == md52.split()[3]


async def test_auth():
    async with AppClient(config) as cli:
        resp = await cli.get("/test-auth")
        assert resp.status == 200
        text = await resp.text()
        assert "I'm authenticated as" in text


async def test_service():
    async with AppClient(config) as cli:
        resp = await cli.get("/test-service")
        assert resp.status == 200
        text = await resp.text()
        assert "staging service version" in text


async def test_jbi_metadata():
    txt = "testing text\n"
    username = "testuser"
    jbi_metadata = '{"file_owner": "sdm", "added_date": "2013-08-12T00:21:53.844000"}'

    async with AppClient(config, username) as cli:
        with FileUtil() as fs:
            d = fs.make_dir(os.path.join(username, "test"))
            f = fs.make_file(os.path.join(username, "test", "test_jgi.fastq"), txt)
            f_jgi = fs.make_file(
                os.path.join(username, "test", ".test_jgi.fastq.jgi"), jbi_metadata
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


async def test_metadata():
    txt = "testing text\n"
    username = "testuser"
    async with AppClient(config, username) as cli:
        with FileUtil() as fs:
            d = fs.make_dir(os.path.join(username, "test"))
            f = fs.make_file(os.path.join(username, "test", "test_file_1"), txt)
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
            assert json.get("lineCount") == "1"
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
            assert json.get("lineCount") == "1"
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
            assert json.get("lineCount") == "1"
            assert json.get("head") == "testing text\n"
            assert json.get("tail") == "testing text\n"
            assert json.get("name") == "test_file_1"
            assert json.get("size") == 13
            assert not json.get("isFolder")


async def test_define_UPA():
    txt = "testing text\n"
    username = "testuser"
    async with AppClient(config, username) as cli:
        with FileUtil() as fs:
            d = fs.make_dir(os.path.join(username, "test"))
            f = fs.make_file(os.path.join(username, "test", "test_file_1"), txt)
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
            assert "succesfully updated UPA test_UPA" in json_text

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
                headers={"Authorization": ""},
                data={"UPA": "test_UPA"},
            )
            assert res4.status == 404

            # tesging missing body
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


async def test_mv():
    txt = "testing text\n"
    username = "testuser"
    async with AppClient(config, username) as cli:
        with FileUtil() as fs:
            d = fs.make_dir(os.path.join(username, "test"))
            f = fs.make_file(os.path.join(username, "test", "test_file_1"), txt)

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


async def test_delete():
    txt = "testing text\n"
    username = "testuser"
    async with AppClient(config, username) as cli:
        with FileUtil() as fs:
            d = fs.make_dir(os.path.join(username, "test"))
            f = fs.make_file(os.path.join(username, "test", "test_file_1"), txt)

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


async def test_list():
    txt = "testing text"
    username = "testuser"
    async with AppClient(config, username) as cli:
        with FileUtil() as fs:
            d = fs.make_dir(os.path.join(username, "test"))
            f = fs.make_file(os.path.join(username, "test", "test_file_1"), txt)
            d2 = fs.make_dir(os.path.join(username, "test", "test_sub_dir"))
            f3 = fs.make_file(
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
            f4 = fs.make_file(os.path.join(username, "test", ".test_file_1"), txt)
            # f5 = fs.make_file(os.path.join(username, 'test', '.globus_id'), txt)
            res6 = await cli.get("/list/", headers={"Authorization": ""})
            assert res6.status == 200
            json_text = await res6.text()
            json = decoder.decode(json_text)

            file_names = [
                file_json["name"] for file_json in json if not file_json["isFolder"]
            ]
            assert ".test_file_1" in file_names
            assert ".globus_id" not in file_names
            assert len(file_names) == 3

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


@asyncgiven(txt=st.text())
async def test_download(txt):
    username = "testuser"
    async with AppClient(config, username) as cli:
        with FileUtil() as fs:
            d = fs.make_dir(os.path.join(username, "test"))
            f = fs.make_file(os.path.join(username, "test", "test_file_1"), txt)

            res = await cli.get(
                os.path.join("download", "test", "test_file_1"),
                headers={"Authorization": ""},
            )
            assert res.status == 200
            result_text = await res.read()
            assert result_text == txt.encode()


async def test_download_errors():
    username = "testuser"
    async with AppClient(config, username) as cli:
        with FileUtil() as fs:
            d = fs.make_dir(os.path.join(username, "test"))

            res1 = await cli.get("download", headers={"Authorization": ""})
            assert res1.status == 404
            res2 = await cli.get(
                os.path.join("download", "test", ""), headers={"Authorization": ""}
            )
            assert res2.status == 400


async def test_similar():
    txt = "testing text"
    username = "testuser"
    async with AppClient(config, username) as cli:
        with FileUtil() as fs:
            d = fs.make_dir(os.path.join(username, "test"))
            f = fs.make_file(os.path.join(username, "test", "test_file_1.fq"), txt)
            d1 = fs.make_dir(os.path.join(username, "test", "test_sub_dir"))
            f1 = fs.make_file(
                os.path.join(username, "test", "test_sub_dir", "test_file_2.fq"), txt
            )
            f2 = fs.make_file(
                os.path.join(username, "test", "test_sub_dir", "test_file_right.fq"),
                txt,
            )
            f3 = fs.make_file(
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


async def test_existence():
    txt = "testing text"
    username = "testuser"
    async with AppClient(config, username) as cli:
        with FileUtil() as fs:
            d = fs.make_dir(os.path.join(username, "test"))
            f = fs.make_file(os.path.join(username, "test", "test_file_1"), txt)
            d2 = fs.make_dir(os.path.join(username, "test", "test_sub_dir"))
            f3 = fs.make_file(
                os.path.join(username, "test", "test_sub_dir", "test_file_2"), txt
            )
            d3 = fs.make_dir(
                os.path.join(username, "test", "test_sub_dir", "test_file_1")
            )
            d4 = fs.make_dir(
                os.path.join(username, "test", "test_sub_dir", "test_sub_dir")
            )
            f4 = fs.make_file(
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


async def test_search():
    txt = "testing text"
    username = "testuser"
    async with AppClient(config, username) as cli:
        with FileUtil() as fs:
            d = fs.make_dir(os.path.join(username, "test"))
            f = fs.make_file(os.path.join(username, "test", "test1"), txt)
            d2 = fs.make_dir(os.path.join(username, "test", "test2"))
            f3 = fs.make_file(os.path.join(username, "test", "test2", "test3"), txt)
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


async def test_upload():
    txt = "testing text\n"
    username = "testuser"
    async with AppClient(config, username) as cli:
        # tesging missing body
        res1 = await cli.post("upload", headers={"Authorization": ""})
        assert res1.status == 400

        with FileUtil() as fs:
            d = fs.make_dir(os.path.join(username, "test"))
            f = fs.make_file(os.path.join(username, "test", "test_file_1"), txt)

            files = {"destPath": "/", "uploads": open(f, "rb")}

            res2 = await cli.post(
                os.path.join("upload"), headers={"Authorization": ""}, data=files
            )

            assert res2.status == 200

            # test upload file with leading space
            f2 = fs.make_file(os.path.join(username, "test", " test_file_1"), txt)

            files = {"destPath": "/", "uploads": open(f2, "rb")}

            res3 = await cli.post(
                os.path.join("upload"), headers={"Authorization": ""}, data=files
            )

            assert res3.status == 403


@settings(deadline=None)
@asyncgiven(contents=st.text())
async def test_directory_decompression(contents):
    fname = "test"
    dirname = "dirname"
    username = "testuser"
    path = utils.Path.validate_path(username, os.path.join(dirname, fname))
    path2 = utils.Path.validate_path(username, os.path.join(dirname, fname))
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
    async with AppClient(config, username) as cli:
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


@asyncgiven(contents=st.text())
async def test_file_decompression(contents):
    fname = "test"
    dirname = "dirname"
    username = "testuser"
    path = utils.Path.validate_path(username, os.path.join(dirname, fname))
    if path.user_path.endswith("/"):
        # invalid test case
        # TODO it should be faster if hypothesis could generate all cases except these
        return
    methods = [("gzip", ".gz"), ("bzip2", ".bz2")]
    async with AppClient(config, username) as cli:
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


async def test_importer_mappings():
    """
    This tests calling with simple good cases, and some expected bad cases
    :return:
    """
    username = "testuser"

    # Normal case, no match
    data = {"file_list": ["file1.txt"]}
    qs1 = urlencode(data, doseq=True)

    async with AppClient(config, username) as cli:
        resp = await cli.get(f"importer_mappings/?{qs1}")
        assert resp.status == 200
        text = await resp.json()
        assert "mappings" in text
        mappings = text["mappings"]
        assert mappings[0] is None

    # Normal case, one match
    data = {"file_list": ["file1.txt", "file.tar.gz"]}
    qs2 = urlencode(data, doseq=True)

    async with AppClient(config, username) as cli:
        resp = await cli.get(f"importer_mappings/?{qs2}", data=data)
        assert resp.status == 200
        text = await resp.json()
        assert "mappings" in text
        mappings = text["mappings"]
        assert mappings[0] is None
        # As we update the app mappings this test may need to be changed
        # Or we need to reload json file itself

        # unzip_mapping = AutoDetectUtils._MAPPINGS["apps"]["decompress/unpack"]
        assert mappings[1][0] == AutoDetectUtils._MAPPINGS["types"]["gz"][0]

    # A dict is passed in
    data = {"file_list": [{}]}
    qs3 = urlencode(data, doseq=True)
    async with AppClient(config, username) as cli:
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
        async with AppClient(config, username) as cli:
            resp = await cli.get(f"importer_mappings/?{qsd}")
            assert resp.status == 400
            text = await resp.text()
            assert "must provide file_list field" in text
