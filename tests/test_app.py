import staging_service.app as app
import staging_service.utils as utils
import pytest
import configparser
import string
import os
import asyncio
from hypothesis import given
from hypothesis import strategies as st
import hashlib

config = configparser.ConfigParser()
config.read(os.environ['KB_DEPLOYMENT_CONFIG'])

DATA_DIR = config['staging_service']['DATA_DIR']
META_DIR = config['staging_service']['META_DIR']
AUTH_URL = config['staging_service']['AUTH_URL']


@pytest.fixture
def cli(loop, test_client):
    appplication = app.app_factory(config)
    return loop.run_until_complete(test_client(appplication))


class FileUtil(object):
    def __init__(self, base_dir=DATA_DIR):
        self.resources = []
        self.base_dir = base_dir

    def teardown(self):
        for created_file in self.resources:
            try:  # trying to clean up cleanly
                os.remove(created_file)
                os.removedirs(os.path.dirname(created_file))
            except OSError as still_files:
                pass

    def make_file(self, path, contents):
        path = os.path.join(self.base_dir, path)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, mode='w') as f:
            f.write(contents)
        self.resources.append(path)
        return path

    def make_dir(self, path):
        path = os.path.join(self.base_dir, path)
        os.makedirs(path, exist_ok=True)
        return path


async def test_service(cli):
    resp = await cli.get('/test-service')
    assert resp.status == 200
    text = await resp.text()
    assert 'This is just a test. This is only a test.' in text

first_letter_alphabet = [c for c in string.ascii_lowercase+string.ascii_uppercase]
username_alphabet = [c for c in '_'+string.ascii_lowercase+string.ascii_uppercase]
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

# @given(txt=st.text())
# def test_wrapper(*args, **kwargs):
#     async def test_cmd(txt):
#         fs = FileUtil()
#         d = fs.make_dir('test')
#         one = await utils.run_command('ls', d)
#         assert '' == one
#         f = fs.make_file(d + '/test2', txt)
#         # two = await utils.run_command('ls', d)
#         # assert 'test2' == two
#         three = await utils.run_command('cat', f)
#         assert txt == three
#     loop = asyncio.new_event_loop()
#     asyncio.set_event_loop(loop)
#     future = asyncio.wait_for(test_cmd(*args, **kwargs), timeout=5)
#     loop.run_until_complete(future)


def asyncgiven(**kwargs):
    def real_decorator(fn):
        @given(**kwargs)
        def aio_wrapper(*args, **kwargs):
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            future = asyncio.wait_for(fn(*args, **kwargs), timeout=5)
            loop.run_until_complete(future)
        return aio_wrapper
    return real_decorator


@asyncgiven(txt=st.text())
async def test_cmd(txt):
    fs = FileUtil()
    d = fs.make_dir('test')
    assert '' == await utils.run_command('ls', d)
    f = fs.make_file(d + '/test2', txt)
    md5 = hashlib.md5(txt.encode('utf8')).hexdigest()
    md52 = await utils.run_command('md5sum', f)
    assert md5 == md52.split()[0]
    fs.teardown()


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
