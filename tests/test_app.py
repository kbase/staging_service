import staging_service.app as app
import staging_service.utils as utils
import staging_service.metadata as metadata
import pytest
import configparser
import string
import os
import asyncio
from hypothesis import given, seed
from hypothesis import strategies as st
import hashlib
import uvloop
import shutil
from aiohttp import test_utils

config = configparser.ConfigParser()
config.read(os.environ['KB_DEPLOYMENT_CONFIG'])

DATA_DIR = config['staging_service']['DATA_DIR']
META_DIR = config['staging_service']['META_DIR']
AUTH_URL = config['staging_service']['AUTH_URL']
utils.Path._DATA_DIR = DATA_DIR
utils.Path._META_DIR = META_DIR


# def client(fn):
#     async def inside(**kwargs):
#         loop = asyncio.get_event_loop()
#         application = app.app_factory(config)

#         async def mock_auth(*args, **kwargs):
#             return 'testuser'
#         app.auth_client.get_user = mock_auth
#         server = test_utils.TestServer(application)
#         await server.start_server(loop=loop)
#         cli = test_utils.TestClient(server, loop=asyncio.get_event_loop())
#         await fn(cli, **kwargs)
#         await server.close()
#     return inside

# @pytest.fixture
# def cli(loop, test_client):
#     appplication = app.app_factory(config)

#     async def mock_auth(*args, **kwargs):
#         return 'testuser'
#     app.auth_client.get_user = mock_auth
#     return loop.run_until_complete(test_client(appplication))


def asyncgiven(**kwargs):
    """alterantive to hypothesis.given decorator for async"""
    def real_decorator(fn):
        @given(**kwargs)
        def aio_wrapper(*args, **kwargs):
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            future = asyncio.wait_for(fn(*args, **kwargs), timeout=5)
            loop.run_until_complete(future)
        return aio_wrapper
    return real_decorator


# def asyncgiven_fixture(**kwargs):
#     """alterantive to hypothesis.given decorator for async and pytest fixture"""
#     def real_decorator(fn):
#         @given(**kwargs)
#         def aio_wrapper(**kwargs):
#             fn
#         return aio_wrapper
#     return real_decorator

class Client():
    def __init__(self, config, mock_username=None):
        application = app.app_factory(config)

        async def mock_auth(*args, **kwargs):
            return 'testuser'
        app.auth_client.get_user = mock_auth
        self.server = test_utils.TestServer(application)

    async def __aenter__(self):
        await self.server.start_server(loop=asyncio.get_event_loop())
        self.client = test_utils.TestClient(self.server, loop=asyncio.get_event_loop())
        return self.client

    async def __aexit__(self, *args):
        await self.server.close()
        await self.client.close()


def mock_auth_app():
    application = app.app_factory(config)

    async def mock_auth(*args, **kwargs):
        return 'testuser'
    app.auth_client.get_user = mock_auth
    return application

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


#
# BEGIN TESTS
#

first_letter_alphabet = [c for c in string.ascii_lowercase+string.ascii_uppercase]
username_alphabet = [c for c in '_'+string.ascii_lowercase+string.ascii_uppercase+string.digits]
username_strat = st.text(max_size=99, min_size=1, alphabet=username_alphabet)
username_first_strat = st.text(max_size=1, min_size=1, alphabet=first_letter_alphabet)


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


# async def test_service():
#     async with Client(config) as cli:
#         resp = await cli.get('/test-service')
#         assert resp.status == 200
#         text = await resp.text()
#         assert 'This is just a test. This is only a test.' in text


async def test_service():
    
    async with test_utils.TestServer(application, loop=asyncio.get_event_loop()) as srv, test_utils.TestClient(srv, loop=asyncio.get_event_loop()) as cli:
            resp = await cli.get('/test-service')
            assert resp.status == 200
            text = await resp.text()
            assert 'This is just a test. This is only a test.' in text
    


# @asyncgiven_fixture(txt=st.text())
# async def test_list(cli, txt):
#     fs = FileUtil()
#     d = fs.make_dir('test')
#     f = fs.make_file('test/test1', txt)
#     d2 = fs.make_dir('test/test2')
#     f3 = fs.make_file('test/test2/test3', txt)
#     cli.get('list/..') # should error
#     cli.get('list/test1') # should tell me its a file not a dir
#     # for both below check info of size compared to txt
#     # check the size of folders is equal to adding up thier contents
#     # check that mtime is older than now
#     # verify isfolder field
#     cli.get('list/')
#     cli.get('list/test2')
#     fs.teardown()


# @asyncgiven(contents=st.text())
# async def test_targz(contents):
#     fname = 'test'
#     dirname = 'dirname'
#     username = 'testuser'
#     path = utils.Path.validate_path(username, os.path.join(dirname, fname))
#     path2 = utils.Path.validate_path(username, os.path.join(dirname, fname))
#     if path.user_path.endswith('/') or path2.user_path.endswith('/'):
#         # invalid test case
#         # TODO it should be faster if hypothesis could generate all cases except these
#         return
#     methods = [
#         ('gztar', '.tgz'),
#         ('gztar', '.tar.gz'),
#         ('zip', '.zip'),
#         ('zip', '.ZIP'),
#         ('bztar', '.tar.bz2'),
#         ('bztar', '.tar.bz'),
#         ('tar', '.tar')
#     ]
#     async with Client(config, username) as cli:
#         for method, extension in methods:
#             with FileUtil() as fs:
#                 d = fs.make_dir(os.path.join(username, dirname))
#                 f1 = fs.make_file(path.user_path, contents)
#                 d2 = fs.make_dir(os.path.join(username, dirname, dirname))
#                 f3 = fs.make_file(path2.user_path, contents)
#                 # end common test code
#                 compressed = shutil.make_archive(d, method, base_dir=d)
#                 name = dirname + extension
#                 if not compressed.endswith(extension):
#                     basename, _ = os.path.splitext(compressed)
#                     basename, _ = os.path.splitext(basename)
#                     # this should handle the .stuff.stuff case as well as .stuff
#                     # it won't handle any more though such as .stuff.stuff.stuff
#                     new_name = basename+extension
#                     os.rename(compressed, new_name)
#                     compressed = new_name
#                 shutil.rmtree(d)
#                 # check to see that the originals are gone
#                 assert not os.path.exists(d)
#                 assert not os.path.exists(f1)
#                 assert not os.path.exists(d2)
#                 assert not os.path.exists(f3)
#                 assert os.path.exists(compressed)
#                 resp = await cli.patch('/decompress/'+name, headers={'Authorization': ''})
#                 assert resp.status == 200
#                 text = await resp.text()
#                 assert 'succesfully decompressed' in text
#                 assert name in text
#                 # check to see if we got back what we started with for all files and directories
#                 assert os.path.exists(d)
#                 assert os.path.exists(d)
#                 assert os.path.exists(f1)
#                 assert os.path.exists(d2)
#                 assert os.path.exists(f3)
#     ...


# @asyncgiven(contents=st.text())
# async def test_gzip(contents):
#     fname = 'test'
#     dirname = 'dirname'
#     username = 'testuser'
#     path = utils.Path.validate_path(username, os.path.join(dirname, fname))
#     if path.user_path.endswith('/'):
#         # invalid test case
#         # TODO it should be faster if hypothesis could generate all cases except these
#         return
#     methods = [
#         ('gzip', '.gz'),
#         ('bzip2', '.bz2')
#     ]
#     async with Client(config, username) as cli:
#         for method, extension in methods:
#             with FileUtil() as fs:
#                 d = fs.make_dir(os.path.join(username, dirname))
#                 f1 = fs.make_file(path.user_path, contents)
#                 name = fname + extension
#                 full_name = f1 + extension
#                 await utils.run_command(method, f1)
#                 if not full_name.endswith(extension):
#                     os.rename(full_name, f1+extension)
#                 # check to see that the original is gone
#                 os.remove(f1)
#                 assert os.path.exists(d)
#                 assert not os.path.exists(f1)
#                 assert os.path.exists(os.path.join(d, name))
#                 resp = await cli.patch('/decompress/'+os.path.join(d, name), headers={'Authorization': ''})
#                 assert resp.status == 200
#                 text = await resp.text()
#                 assert 'succesfully decompressed' in text
#                 assert name in text
#                 # check to see if we got back what we started with for all files and directories
#                 assert os.path.exists(d)
#                 assert os.path.exists(f1)


# @asyncgiven(txt=st.text())
# async def test_generate_metadata():
#     fs = FileUtil
# async def test_generate_metadata_binary(parameter_list):
#     pass

# async def test_cmd(parameter_list):

# @given(st.lists(st.integers()))
# def test_sort(xs):
#     sorted_xs = list(sorted(xs))
#     assert isinstance(sorted_xs, list)
#     assert len(xs) == len(sorted_xs)
#     assert all(
#         x <= y for x, y in
#         zip(sorted_xs, sorted_xs[1:])
#     )


# @hypothesis.given(#stuf)
# def test_against_brute_force(input):
#     assert (
#         #simple filesystem task
#         ==
#         # api calls
#     )


# @given(st.text())
# def test_data_feeder(text):
#     async def test_service2(cli):
#         resp = await cli.get('/test-service')
#         assert resp.status == 200
#         text = await resp.text()
#         assert 'This is just a test. This is only a test.' in text