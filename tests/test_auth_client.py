import pytest
import time
from staging_service.auth2Client import TokenCache, KBaseAuth2, TOKEN_PATH, USERNAME_PATH
from aiohttp import web
from aioresponses import aioresponses

FAKE_AUTH_URL = "https://fake_auth_url"


# TokenCache tests
# ----------------
def test_token_cache_get_add_valid_token():
    cache = TokenCache()
    token = "mytoken"
    user = "testuser"
    expire = int(time.time()) + 100

    # Initially returns None
    assert cache.get_user(token) is None

    # Add token
    cache.add_valid_token(token, user, expire)
    assert cache.get_user(token) == user


def test_token_cache_expired_token():
    cache = TokenCache()
    token = "mytoken"
    user = "testuser"
    expire = int(time.time()) - 10  # expired
    cache.add_valid_token(token, user, expire)

    assert cache.get_user(token) is None


def test_token_cache_missing_token_or_user():
    cache = TokenCache()
    with pytest.raises(web.HTTPBadRequest) as err:
        cache.add_valid_token("", "user", int(time.time()) + 100)
    assert err.value.text == "Must supply token"
    with pytest.raises(web.HTTPBadRequest) as err:
        cache.add_valid_token("token", "", int(time.time()) + 100)
    assert err.value.text == "Must supply user"


def test_cache_overflow():
    # This one digs a little deep into implementation details like cache sizing and resizing.
    max_size = 10
    cache = TokenCache(maxsize=max_size)
    for i in range(max_size):
        cache.add_valid_token(f"token-{i}", f"user-{i}", time.time() + 100)
    # assert it's actually full
    assert len(cache._cache) == max_size
    overflow_token = "overflow-token"
    overflow_user = "overflow-user"
    cache.add_valid_token(overflow_token, overflow_user, time.time() + 100)
    # now it should be half full
    assert len(cache._cache) == cache._halfmax
    # but the last added token should be in there
    assert cache.get_user(overflow_token) == overflow_user


# Auth client tests
# -----------------
@pytest.mark.asyncio
async def test_get_user_from_cache():
    auth = KBaseAuth2(FAKE_AUTH_URL)
    token = "mytoken"
    user = "cacheduser"
    expire = int(time.time()) + 100

    # seed the cache with the token, avoids lookup
    auth._cache.add_valid_token(token, user, expire)

    result = await auth.get_user(token)
    assert result == user


@pytest.mark.asyncio
async def test_get_user_from_service():
    token = "mytoken"
    user = "testuser"
    token_url = f"{FAKE_AUTH_URL}{TOKEN_PATH}"

    with aioresponses() as mock:
        mock.get(
            token_url,
            payload={"user": user, "expires": int(time.time()) + 100, "cachefor": 300},
            status=200,
            reason="OK",
        )

        auth = KBaseAuth2(FAKE_AUTH_URL)
        result = await auth.get_user(token)
        assert result == user


@pytest.mark.asyncio
@pytest.mark.parametrize("token", ["", None])
async def test_get_user_no_token(token):
    with pytest.raises(web.HTTPBadRequest) as err:
        auth = KBaseAuth2(FAKE_AUTH_URL)
        await auth.get_user(token)
    assert err.value.text == "Must supply token"


@pytest.mark.asyncio
async def test_get_user_fail():
    token_url = f"{FAKE_AUTH_URL}{TOKEN_PATH}"
    with aioresponses() as mock:
        mock.get(
            token_url,
            payload={"error": {"httpcode": 403, "message": "Forbidden"}},
            status=403,
            reason="Forbidden",
        )
        auth = KBaseAuth2(FAKE_AUTH_URL)
        with pytest.raises(web.HTTPUnauthorized) as err:
            await auth.get_user("token")
        assert err.value.text == "Error connecting to auth service: 403 Forbidden\nForbidden"


@pytest.mark.asyncio
async def test_check_user_exists():
    username = "someuser"
    check_url = f"{FAKE_AUTH_URL}{USERNAME_PATH}{username}"

    with aioresponses() as mock:
        # means the username is taken
        mock.get(check_url, payload={"availablename": "someuser1"}, status=200, reason="OK")

        auth = KBaseAuth2(FAKE_AUTH_URL)
        assert await auth.check_user_exists(username)


@pytest.mark.asyncio
async def test_check_user_not_exist():
    username = "someuser"
    check_url = f"{FAKE_AUTH_URL}{USERNAME_PATH}{username}"

    with aioresponses() as mock:
        # means the username is still available
        mock.get(check_url, payload={"availablename": username}, status=200, reason="OK")

        auth = KBaseAuth2(FAKE_AUTH_URL)
        assert not await auth.check_user_exists(username)


@pytest.mark.asyncio
async def test_check_user_exists_fail():
    username = "someuser"
    with aioresponses() as mock:
        mock.get(
            f"{FAKE_AUTH_URL}{USERNAME_PATH}{username}",
            payload={"error": {"httpcode": 500, "message": "internal server error"}},
            status=500,
            reason="failed",
        )
        auth = KBaseAuth2(FAKE_AUTH_URL)
        with pytest.raises(web.HTTPError) as err:
            await auth.check_user_exists(username)
        assert (
            err.value.text == "Error connecting to auth service: 500 failed\ninternal server error"
        )


@pytest.mark.asyncio
async def test_check_user_exists_fail_bad_response():
    username = "someuser"
    with aioresponses() as mock:
        mock.get(f"{FAKE_AUTH_URL}{USERNAME_PATH}{username}", payload={}, status=200, reason="OK")
        auth = KBaseAuth2(FAKE_AUTH_URL)
        with pytest.raises(web.HTTPError) as err:
            await auth.check_user_exists(username)
        assert (
            err.value.text
            == "Malformed response from auth service: 'availablename' key not in response"
        )
