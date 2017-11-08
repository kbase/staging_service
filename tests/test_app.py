import staging_service.app as app
import staging_service.utils as utils
import pytest
import configparser
import string
import os
from hypothesis import given
from hypothesis import strategies as st

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
    def __init__(self, base_dir):
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

    def make_dir(self, path):
        path = os.path.join(self.base_dir, path)
        os.makedirs(path, exist_ok=True)

    def binary_file(self, path):
        self.make_file(os.urandom(2048))


async def test_service(cli):
    resp = await cli.get('/test-service')
    assert resp.status == 200
    text = await resp.text()
    assert 'This is just a test. This is only a test.' in text


username_alphabet = [c for c in '_'+string.ascii_lowercase+string.ascii_uppercase]
username_strat = st.text(max_size=100, min_size=1, alphabet=username_alphabet)


@given(username_strat)
def test_path_cases(username):
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


@given(username_strat, st.text())
def test_path_sanitation(username, path):
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



# TODO should I have constraints on text
# @given(st.text(), st.text())
# def test_path_sanitation(username, path):
#     validated = utils.Path.validate_path(username, path)
#     dumb

# notes


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

