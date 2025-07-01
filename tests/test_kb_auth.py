import asyncio
import pytest
from staging_service.kb_auth_client import InvalidUserError, KBaseAuth, InvalidTokenError, _get
from tests.test_utils import bootstrap_config
import os
from unittest.mock import patch

config = bootstrap_config()
AUTH_URL = config["staging_service"]["AUTH_URL"]

# NOTE: These tests are intended to be run against the auth service at
# https://ci.kbase.us/services/auth
# Any unexpected failures should check the auth service, the given test
# token, and whether the test user exists or not.

# TODO: add env var names to test config
TEST_TOKEN = os.environ.get("KBASE_TEST_TOKEN")
TEST_USER = os.environ.get("KBASE_TEST_USER")
VALID_TEST_USER = "narrativetest"
NOT_REAL_USER = "please_do_not_ever_make_this_username_what_is_wrong_with_you"
INVALID_USER = "_(__)_"


@pytest.fixture
async def auth_client():
    """
    Makes a default auth client with a shiny new cache.
    """
    return await KBaseAuth.create(AUTH_URL)


async def test_create():
    auth_client = await KBaseAuth.create(AUTH_URL)
    assert isinstance(auth_client, KBaseAuth)


async def test_create_non_auth_url():
    with pytest.raises(IOError, match="does not appear to be the KBase Authentication Service"):
        await KBaseAuth.create("https://github.com")


async def test_create_incorrect_url():
    with pytest.raises(IOError, match="Error from KBase auth server"):
        await KBaseAuth.create(AUTH_URL + "wrong")


async def test_non_json_error():
    with pytest.raises(IOError, match="Non-JSON response from KBase auth server"):
        await KBaseAuth.create("https://kbase.us/services")


# TODO: test other service fail modes


async def test_get_user(auth_client: KBaseAuth):
    assert await auth_client.get_user(TEST_TOKEN) == TEST_USER


async def test_get_user_from_cache(auth_client: KBaseAuth):
    # patch this to act as a spy, should only be called once with the caching done.
    with patch("staging_service.kb_auth_client._get", wraps=_get) as spy_get:
        result = await auth_client.get_user(TEST_TOKEN)
        assert result == TEST_USER

        result = await auth_client.get_user(TEST_TOKEN)
        assert result == TEST_USER

        # make sure it's only called once
        spy_get.assert_awaited_once()


async def test_get_user_drop_cache():
    auth_client = await KBaseAuth.create(AUTH_URL, cache_expiration=1)
    with patch("staging_service.kb_auth_client._get", wraps=_get) as spy_get:
        result = await auth_client.get_user(TEST_TOKEN)
        assert result == TEST_USER

        result = await auth_client.get_user(TEST_TOKEN)
        assert result == TEST_USER

        # make sure it's only called once at this point
        spy_get.assert_awaited_once()
        await asyncio.sleep(1)

        # cache should have dropped the user
        result = await auth_client.get_user(TEST_TOKEN)
        assert result == TEST_USER

        # expect this to be 2
        assert spy_get.call_count == 2


# TODO: test cache max size?


@pytest.mark.parametrize("token", ["", None])
async def test_get_user_no_token(auth_client: KBaseAuth, token: str | None):
    with pytest.raises(ValueError, match="token is required"):
        await auth_client.get_user(token)


async def test_get_user_fail(auth_client: KBaseAuth):
    with pytest.raises(InvalidTokenError, match="token is invalid"):
        await auth_client.get_user("some_token")


async def test_is_valid_user(auth_client: KBaseAuth):
    assert await auth_client.is_valid_user(VALID_TEST_USER, TEST_TOKEN)


async def test_is_valid_user_not_exist(auth_client: KBaseAuth):
    assert not await auth_client.is_valid_user(NOT_REAL_USER, TEST_TOKEN)


async def test_is_valid_user_invalid(auth_client: KBaseAuth):
    with pytest.raises(InvalidUserError, match="Illegal character in user name"):
        await auth_client.is_valid_user(INVALID_USER, TEST_TOKEN)


async def test_is_valid_user_fail(auth_client: KBaseAuth):
    with pytest.raises(InvalidTokenError, match="token is invalid"):
        await auth_client.is_valid_user(VALID_TEST_USER, "fake_token")
