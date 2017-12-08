import staging_service.app as app
import staging_service.utils as utils
import staging_service.metadata as metadata
import staging_service.globus as globus
import configparser
import string
import os
import asyncio
from hypothesis import given, seed, settings
from hypothesis import strategies as st
import hashlib
import uvloop
import shutil
from aiohttp import test_utils
from json import JSONDecoder
import time

decoder = JSONDecoder()

config = configparser.ConfigParser()
config.read(os.environ['KB_DEPLOYMENT_CONFIG'])

DATA_DIR = config['staging_service']['DATA_DIR']
META_DIR = config['staging_service']['META_DIR']
AUTH_URL = config['staging_service']['AUTH_URL']
if DATA_DIR.startswith('.'):
    DATA_DIR = os.path.normpath(os.path.join(os.getcwd(), DATA_DIR))
if META_DIR.startswith('.'):
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
        return 'testuser'
    app.auth_client.get_user = mock_auth

    async def mock_globus_id(*args, **kwargs):
        return ['testuser@globusid.org']
    globus._get_globus_ids = mock_globus_id  # TODO this doesn't allow testing of this fn does it
    return application


class AppClient():
    def __init__(self, config, mock_username=None):
        self.server = test_utils.TestServer(mock_auth_app())

    async def __aenter__(self):
        await self.server.start_server(loop=asyncio.get_event_loop())
        self.client = test_utils.TestClient(self.server, loop=asyncio.get_event_loop())
        return self.client

    async def __aexit__(self, *args):
        await self.server.close()
        await self.client.close()


class FileUtil():
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
        with open(path, encoding='utf-8', mode='w') as f:
            f.write(contents)
        return path

    def make_dir(self, path):
        path = os.path.join(self.base_dir, path)
        os.makedirs(path, exist_ok=True)
        return path


first_letter_alphabet = [c for c in string.ascii_lowercase+string.ascii_uppercase]
username_alphabet = [c for c in '_'+string.ascii_lowercase+string.ascii_uppercase+string.digits]
username_strat = st.text(max_size=99, min_size=1, alphabet=username_alphabet)
username_first_strat = st.text(max_size=1, min_size=1, alphabet=first_letter_alphabet)

#
# BEGIN TESTS
#


@given(username_first_strat, username_strat)
def test_path_cases(username_first, username_rest):
    username = username_first + username_rest
    assert username + '/foo/bar' == utils.Path.validate_path(username, 'foo/bar').user_path
    assert username + '/baz' == utils.Path.validate_path(username, 'foo/../bar/../baz').user_path
    assert username + '/bar' == utils.Path.validate_path(username, 'foo/../../../../bar').user_path
    assert username + '/foo' == utils.Path.validate_path(username, './foo').user_path
    assert username + '/foo/bar' == utils.Path.validate_path(username, '../foo/bar').user_path
    assert username + '/foo' == utils.Path.validate_path(username, '/../foo').user_path
    assert username + '/' == utils.Path.validate_path(username, '/foo/..').user_path
    assert username + '/foo' == utils.Path.validate_path(username, '/foo/.').user_path
    assert username + '/foo' == utils.Path.validate_path(username, 'foo/').user_path
    assert username + '/foo' == utils.Path.validate_path(username, 'foo').user_path
    assert username + '/foo' == utils.Path.validate_path(username, '/foo/').user_path
    assert username + '/foo' == utils.Path.validate_path(username, '/foo').user_path
    assert username + '/foo' == utils.Path.validate_path(username, 'foo/.').user_path
    assert username + '/' == utils.Path.validate_path(username, '').user_path
    assert username + '/' == utils.Path.validate_path(username, 'foo/..').user_path
    assert username + '/' == utils.Path.validate_path(username, '/..../').user_path
    assert username + '/stuff.ext' == utils.Path.validate_path(username, '/stuff.ext').user_path


@given(username_first_strat, username_strat, st.text())
def test_path_sanitation(username_first, username_rest, path):
    username = username_first + username_rest
    validated = utils.Path.validate_path(username, path)
    assert validated.full_path.startswith(DATA_DIR)
    assert validated.user_path.startswith(username)
    assert validated.metadata_path.startswith(META_DIR)
    assert validated.full_path.find('/..') == -1
    assert validated.user_path.find('/..') == -1
    assert validated.metadata_path.find('/..') == -1
    assert validated.full_path.find('../') == -1
    assert validated.user_path.find('../') == -1
    assert validated.metadata_path.find('../') == -1


@asyncgiven(txt=st.text())
async def test_cmd(txt):
    with FileUtil(DATA_DIR) as fs:
        d = fs.make_dir('test')
        assert '' == await utils.run_command('ls', d)
        f = fs.make_file('test/test2', txt)
        md5 = hashlib.md5(txt.encode('utf8')).hexdigest()
        md52 = await utils.run_command('md5sum', f)
        assert md5 == md52.split()[0]


async def test_service():
    async with AppClient(config) as cli:
        resp = await cli.get('/test-service')
        assert resp.status == 200
        text = await resp.text()
        assert 'This is just a test. This is only a test.' in text


async def test_list():
    txt = 'testing text'
    username = 'testuser'
    async with AppClient(config, username) as cli:
        with FileUtil() as fs:
            d = fs.make_dir(os.path.join(username, 'test'))
            f = fs.make_file(os.path.join(username, 'test', 'test_file_1'), txt)
            d2 = fs.make_dir(os.path.join(username, 'test', 'test_sub_dir'))
            f3 = fs.make_file(os.path.join(username, 'test', 'test_sub_dir', 'test_file_2'), txt)
            res1 = await cli.get('list/..', headers={'Authorization': ''})
            assert res1.status == 404
            res2 = await cli.get(os.path.join('list', 'test', 'test_file_1'),
                                 headers={'Authorization': ''})
            assert res2.status == 400

            # testing root directory with 'list/' routes
            res3 = await cli.get('/list/', headers={'Authorization': ''})
            assert res3.status == 200
            json_text = await res3.text()
            json = decoder.decode(json_text)
            file_folder_count = [file_json['isFolder'] for file_json in json]
            assert json[0]['isFolder'] is True
            assert json[0]['name'] == 'test'
            assert json[0]['path'] == 'testuser/test'
            assert json[0]['mtime'] <= time.time()*1000
            assert len(file_folder_count) == 4  # 2 folders and 2 files
            assert sum(file_folder_count) == 2

            # testing root directory with 'list' route
            res4 = await cli.get('/list', headers={'Authorization': ''})
            assert res4.status == 200
            json_text = await res4.text()
            json = decoder.decode(json_text)
            file_folder_count = [file_json['isFolder'] for file_json in json]
            assert json[0]['isFolder'] is True
            assert json[0]['name'] == 'test'
            assert json[0]['path'] == 'testuser/test'
            assert json[0]['mtime'] <= time.time()*1000
            assert len(file_folder_count) == 4  # 2 folders and 2 files
            assert sum(file_folder_count) == 2

            # testing sub-directory
            res5 = await cli.get(os.path.join('list', 'test'),
                                 headers={'Authorization': ''})
            assert res5.status == 200
            json_text = await res5.text()
            json = decoder.decode(json_text)
            file_folder_count = [file_json['isFolder'] for file_json in json]
            # 1 sub-directory, 1 file in sub-directory and 1 file in root
            assert len(file_folder_count) == 3
            assert sum(file_folder_count) == 1


async def test_existence():
    txt = 'testing text'
    username = 'testuser'
    async with AppClient(config, username) as cli:
        with FileUtil() as fs:
            d = fs.make_dir(os.path.join(username, 'test'))
            f = fs.make_file(os.path.join(username, 'test', 'test_file_1'), txt)
            d2 = fs.make_dir(os.path.join(username, 'test', 'test_sub_dir'))
            f3 = fs.make_file(os.path.join(username, 'test', 'test_sub_dir', 'test_file_2'), txt)
            d3 = fs.make_dir(os.path.join(username, 'test', 'test_sub_dir', 'test_file_1'))
            d4 = fs.make_dir(os.path.join(username, 'test', 'test_sub_dir', 'test_sub_dir'))
            f4 = fs.make_file(os.path.join(username, 'test', 'test_sub_dir',
                                           'test_sub_dir', 'test_file_1'), txt)

            # testing existence of both file and folder name
            res1 = await cli.get('existence/test_file_1', headers={'Authorization': ''})
            assert res1.status == 200
            json_text = await res1.text()
            json = decoder.decode(json_text)
            assert json['exists'] is True
            assert json['format'] == 'Both File and Folder'

            # testing existence of file
            res2 = await cli.get('existence/test_file_2',
                                 headers={'Authorization': ''})
            assert res2.status == 200
            json_text = await res2.text()
            json = decoder.decode(json_text)
            assert json['exists'] is True
            assert json['format'] == 'File'

            # testing existence of folder
            res3 = await cli.get('existence/test_sub_dir',
                                 headers={'Authorization': ''})
            assert res3.status == 200
            json_text = await res3.text()
            json = decoder.decode(json_text)
            assert json['exists'] is True
            assert json['format'] == 'Folder'

            # testing non-existence
            res4 = await cli.get('existence/fake_file', headers={'Authorization': ''})
            assert res4.status == 200
            json_text = await res4.text()
            json = decoder.decode(json_text)
            assert json['exists'] is False
            assert json['format'] == 'N/A'

            res5 = await cli.get('existence/test_sub', headers={'Authorization': ''})
            assert res5.status == 200
            json_text = await res5.text()
            json = decoder.decode(json_text)
            assert json['exists'] is False
            assert json['format'] == 'N/A'


async def test_search():
    txt = 'testing text'
    username = 'testuser'
    async with AppClient(config, username) as cli:
        with FileUtil() as fs:
            d = fs.make_dir(os.path.join(username, 'test'))
            f = fs.make_file(os.path.join(username, 'test', 'test1'), txt)
            d2 = fs.make_dir(os.path.join(username, 'test', 'test2'))
            f3 = fs.make_file(os.path.join(username, 'test', 'test2', 'test3'), txt)
            res1 = await cli.get('search/', headers={'Authorization': ''})
            assert res1.status == 200
            json_text = await res1.text()
            json = decoder.decode(json_text)
            assert len(json) == 4
            res2 = await cli.get('search/test1', headers={'Authorization': ''})
            assert res2.status == 200
            json_text = await res2.text()
            json = decoder.decode(json_text)
            assert len(json) == 1
            res3 = await cli.get('search/test2', headers={'Authorization': ''})
            assert res3.status == 200
            json_text = await res3.text()
            json = decoder.decode(json_text)
            assert len(json) == 2


@settings(deadline=None)
@asyncgiven(contents=st.text())
async def test_directory_decompression(contents):
    fname = 'test'
    dirname = 'dirname'
    username = 'testuser'
    path = utils.Path.validate_path(username, os.path.join(dirname, fname))
    path2 = utils.Path.validate_path(username, os.path.join(dirname, fname))
    if path.user_path.endswith('/') or path2.user_path.endswith('/'):
        # invalid test case
        # TODO it should be faster if hypothesis could generate all cases except these
        return
    methods = [
        ('gztar', '.tgz'),
        ('gztar', '.tar.gz'),
        ('zip', '.zip'),
        ('zip', '.ZIP'),
        ('bztar', '.tar.bz2'),
        ('bztar', '.tar.bz'),
        ('tar', '.tar')
    ]
    async with AppClient(config, username) as cli:
        for method, extension in methods:
            with FileUtil() as fs:
                d = fs.make_dir(os.path.join(username, dirname))
                f1 = fs.make_file(path.user_path, contents)
                d2 = fs.make_dir(os.path.join(username, dirname, dirname))
                f3 = fs.make_file(path2.user_path, contents)
                # end common test code
                compressed = shutil.make_archive(d, method, d[:-len(dirname)], dirname)
                name = dirname + extension
                if not compressed.endswith(extension):
                    basename, _ = os.path.splitext(compressed)
                    basename, _ = os.path.splitext(basename)
                    # this should handle the .stuff.stuff case as well as .stuff
                    # it won't handle any more though such as .stuff.stuff.stuff
                    new_name = basename+extension
                    os.rename(compressed, new_name)
                    compressed = new_name
                shutil.rmtree(d)
                # check to see that the originals are gone
                assert not os.path.exists(d)
                assert not os.path.exists(f1)
                assert not os.path.exists(d2)
                assert not os.path.exists(f3)
                assert os.path.exists(compressed)
                resp = await cli.patch('/decompress/'+name, headers={'Authorization': ''})
                assert resp.status == 200
                text = await resp.text()
                assert 'succesfully decompressed' in text
                assert name in text
                # check to see if we got back what we started with for all files and directories
                assert os.path.exists(d)
                assert os.path.exists(d)
                assert os.path.exists(f1)
                assert os.path.exists(d2)
                assert os.path.exists(f3)


@asyncgiven(contents=st.text())
async def test_file_decompression(contents):
    fname = 'test'
    dirname = 'dirname'
    username = 'testuser'
    path = utils.Path.validate_path(username, os.path.join(dirname, fname))
    if path.user_path.endswith('/'):
        # invalid test case
        # TODO it should be faster if hypothesis could generate all cases except these
        return
    methods = [
        ('gzip', '.gz'),
        ('bzip2', '.bz2'),
    ]
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
                    '/decompress/'+os.path.join(dirname, name),
                    headers={'Authorization': ''})
                assert resp.status == 200
                text = await resp.text()
                assert 'succesfully decompressed' in text
                assert name in text
                # check to see if we got back what we started with for all files and directories
                assert os.path.exists(d)
                assert os.path.exists(f1)
