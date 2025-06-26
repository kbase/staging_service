"""
Created on Aug 1, 2016
A very basic KBase auth client for the Python server.
@author: gaprice@lbl.gov
modified for python3 and authV2
"""

import hashlib
import time as _time

import aiohttp

TOKEN_PATH = "/api/V2/token"
USERNAME_PATH = "/login/suggestname/"


class TokenCache:
    """A basic cache for tokens."""

    _MAX_TIME_SEC = 5 * 60  # 5 min

    def __init__(self, maxsize: int = 2000):
        self._cache = {}
        self._maxsize = maxsize
        self._halfmax = maxsize / 2  # int division to round down

    def get_user(self, token: str):
        token = hashlib.sha256(token.encode("utf8")).hexdigest()
        usertime = self._cache.get(token)
        if not usertime:
            return None

        user, intime, expire_time = usertime
        now = _time.time()
        if now - intime > self._MAX_TIME_SEC or now > expire_time:
            return None
        return user

    def add_valid_token(self, token: str, user: str, expire_time: int):
        if not token:
            raise aiohttp.web.HTTPBadRequest(text="Must supply token")
        if not user:
            raise aiohttp.web.HTTPBadRequest(text="Must supply user")
        token = hashlib.sha256(token.encode("utf8")).hexdigest()
        self._cache[token] = [user, _time.time(), expire_time]
        if len(self._cache) > self._maxsize:
            for i, (t, _) in enumerate(sorted(self._cache.items(), key=lambda v: v[1][1])):
                if i <= self._halfmax:
                    del self._cache[t]
                else:
                    break


class KBaseAuth2:
    """
    A very basic KBase auth client for the Python server.
    """

    def __init__(self, auth_url: str):
        """
        Constructor
        """
        self._authurl = auth_url
        self._cache = TokenCache()

    async def get_user(self, token: str) -> str:
        """
        Takes an auth token, looks up the user info, an returns the username.
        This gets stored in the TokenCache until the token expires, or until
        the token's recorded cache time is up.
        """
        if not token:
            raise aiohttp.web.HTTPBadRequest(text="Must supply token")
        user = self._cache.get_user(token)
        if user:
            return user

        token_url = self._authurl + TOKEN_PATH
        async with aiohttp.ClientSession() as session:
            async with session.get(token_url, headers={"Authorization": token}) as resp:
                ret = await resp.json()
                if resp.reason != "OK":
                    http_code = ret["error"]["httpcode"]
                    message = ret["error"]["message"]
                    raise aiohttp.web.HTTPUnauthorized(
                        text="Error connecting to auth service: "
                        + f"{http_code} {resp.reason}\n{message}"
                    )
        # whichever one comes first
        self._cache._MAX_TIME_SEC = ret["cachefor"]
        self._cache.add_valid_token(token, ret["user"], ret["expires"])
        return ret["user"]

    async def check_user_exists(self, username: str) -> bool:
        """
        Checks whether a kbase user id exists.
        This is implemented in a roundabout way to avoid needing the user's token.
        It uses the /login/suggestname endpoint. If the "availablename" returned
        is different from the given name, then the id exists, and True should
        be returned. If the "availablename" IS the given name, then that isn't
        a user yet, and False is returned.
        """
        check_url = self._authurl + USERNAME_PATH + username
        async with aiohttp.ClientSession() as session:
            async with session.get(check_url) as resp:
                ret = await resp.json()
                if resp.reason != "OK":
                    http_code = ret["error"]["httpcode"]
                    message = ret["error"]["message"]
                    raise aiohttp.web.HTTPError(
                        text=f"Error connecting to auth service: {http_code} {resp.reason}\n{message}"
                    )
                if "availablename" not in ret:
                    raise aiohttp.web.HTTPError(
                        text="Malformed response from auth service: 'availablename' key not in response"
                    )
                return ret["availablename"] != username
