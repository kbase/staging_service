import staging_service.app as app
import staging_service.utils as utils
import staging_service.auth2Client as auth2Client
import aiohttp
import pytest
import configparser
import os
from random import choice, seed
from hypothesis import given
from hypothesis import strategies as st

if __name__ == '__main__':
    main()

config = configparser.ConfigParser()
config.read(os.environ['KB_DEPLOYMENT_CONFIG'])

seed(config['testing']['SEED'])

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
    
    def fasta_file(self, path):
        fa = '> test my testfile\n'
        bases = ['A', 'C', 'G', 'C']
        fa += '\n'.join((''.join((choice(bases) for _ in range())) for _ in range(80)))
        self.make_file(path, fa)
    
    def binary_file(self, path):
        self.make_file(os.urandom(2048))


async def test_service(cli):
    resp = await cli.get('/test-service')
    assert resp.status == 200
    text = await resp.text()
    assert 'This is just a test. This is only a test.' in text

# @given(st.text(), st.text())
# def test_path_sanitation(username, path):
#     """make sure paths always end up in user directory"""

# @given(st.text(average_size=10))
def test_path_cases():
    username = 'test'
    assert username + '/foo/bar' == utils.Path.validate_path(username, 'foo/bar').user_path
    assert username + '/baz' == utils.Path.validate_path(username, 'foo/../bar/../baz').user_path
    assert username + '/bar' == utils.Path.validate_path(username, 'foo/../../../../bar').user_path
    assert username + '/foo' == utils.Path.validate_path(username, './foo').user_path
    assert username + '/foo/bar' == utils.Path.validate_path(username, '../foo/bar').user_path
    assert username + '/foo' == utils.Path.validate_path(username, '/../foo').user_path
    assert username + '/' == utils.Path.validate_path(username, '/foo/..').user_path
    assert username + '/foo/' == utils.Path.validate_path(username, '/foo/.').user_path
    assert username + '/foo/' == utils.Path.validate_path(username, 'foo/').user_path
    assert username + '/foo' == utils.Path.validate_path(username, 'foo').user_path
    assert username + '/foo/' == utils.path.validate_path(username, '/foo/').user_path
    assert username + '/foo' == utils.path.validate_path(username, '/foo').user_path
    assert username + '/foo/' == utils.path.validate_path(username, 'foo/.').user_path
    assert username + '/' == utils.path.validate_path(username, 'foo/..').user_path
    

# TODO should I have constraints on text
# @given(st.text(), st.text())
# def test_path_sanitation(username, path):
#     validated = utils.Path.validate_path(username, path)
#     dumb

# notes


@given(st.lists(st.integers()))
def test_sort(xs):
    sorted_xs = list(sorted(xs))
    assert isinstance(sorted_xs, list)
    assert len(xs) == len(sorted_xs)
    assert all(
        x <= y for x, y in
        zip(sorted_xs, sorted_xs[1:])
    )

# @hypothesis.given(st.text())
# async def test_auth(cli):
#     # do api cal
#     resp = await cli.get()
#     assert response and response.json()
#     assert (response.status_code in  [#all status codes you want])


# @hypothesis.given(#stuf)
# def test_against_brute_force(input):
#     assert (
#         #simple filesystem task
#         ==
#         # api calls
#     )

