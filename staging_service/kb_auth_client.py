"""
A client for the KBase Auth2 server.
"""

# Mostly copied from https://github.com/kbase/cdm-task-service with a few tweaks,
# - included the require_string function
# - removed roles check and management
# TODO make a KBase auth library

import aiohttp
from cacheout.lru import LRUCache
import logging
import time
from typing import Self


async def _get(url: str, headers: dict[str, str]):
    # TODO PERF keep a single session and add a close method
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as r:
            await _check_error(r)
            # TODO: handle edge case where status == 200, but JSON isn't returned
            return await r.json()


async def _check_error(r):
    if r.status != 200:
        try:
            j = await r.json()
        except Exception:
            err = "Non-JSON response from KBase auth server, status code: " + str(r.status)
            logging.getLogger(__name__).info("%s, response:\n%s", err, r.text)
            raise IOError(err)
        # assume that if we get json then at least this is the auth server and we can
        # rely on the error structure.
        err = j["error"].get("appcode")
        if err == 10020:  # Invalid token
            raise InvalidTokenError("KBase auth server reported token is invalid.")
        if err == 30010:  # Illegal username
            # The auth server does some goofy stuff when propagating errors, should be cleaned up
            # at some point
            raise InvalidUserError(j["error"]["message"].split(":", 3)[-1])
        # don't really see any other error codes we need to worry about - maybe disabled?
        # worry about it later.
        raise IOError("Error from KBase auth server: " + j["error"]["message"])


class KBaseAuth:
    """A client for contacting the KBase authentication server."""

    @classmethod
    async def create(
        cls,
        auth_url: str,
        cache_max_size: int = 10000,
        cache_expiration: int = 300,
    ) -> Self:
        """
        Create the client.
        auth_url - The root url of the authentication service.
        cache_max_size -  the maximum size of the token cache.
        cache_expiration -  the expiration time for the token cache in
            seconds.
        """
        if not _require_string(auth_url, "auth_url").endswith("/"):
            auth_url += "/"
        j = await _get(auth_url, {"Accept": "application/json"})
        return KBaseAuth(
            auth_url,
            cache_max_size,
            cache_expiration,
            j.get("servicename"),
        )

    def __init__(
        self,
        auth_url: str,
        cache_max_size: int,
        cache_expiration: int,
        service_name: str,
    ):
        self._url = auth_url
        self._me_url = self._url + "api/V2/me"
        self._cache_timer = time.time  # TODO TEST figure out how to replace the timer to test
        # cache is intended to map tokens -> usernames
        self._cache = LRUCache(
            timer=self._cache_timer, maxsize=cache_max_size, ttl=cache_expiration
        )

        if service_name != "Authentication Service":
            raise IOError(
                f"The service at {self._url} does not appear to be the KBase "
                + "Authentication Service"
            )

        # could use the server time to adjust for clock skew, probably not worth the trouble

    async def get_user(self, token: str) -> str:
        """
        Get a username from a token.

        token - The user's token.

        Returns the user.
        Raises a ValueError if the token is missing
        Raises a InvalidTokenError if the token is invalid
        """
        # TODO CODE should check the token for \n etc.
        _require_string(token, "token")

        if token in self._cache:
            return self._cache.get(token)
        result = await _get(self._me_url, {"Authorization": token})
        self._cache.set(token, result["user"])
        return result["user"]

    async def is_valid_user(self, user: str, token: str) -> bool:
        """
        Check if a user name is valid in the KBase auth service.

        user - the user name to check.
        token - a token to provide to the auth service to allow accessing the lookup endpoint.

        Raises a ValueError if either the user or token is missing
        Raises an InvalidTokenError if the token is invalid
        Raises an InvalidUserError if the username is invalid
        """
        # TODO PERF add a cache here. Currently this is only used by the DTS service to
        # verify a user exists before copying files over, so likely not used often,
        # and likely not a ton of traffic from a single user.
        _require_string(user, "user")
        _require_string(token, "token")
        j = await _get(f"{self._url}api/V2/users/?list={user}", {"Authorization": token})
        return len(j) == 1


class AuthenticationError(Exception):
    """An error thrown from the authentication service."""


class InvalidTokenError(AuthenticationError):
    """An error thrown when a token is invalid."""


class InvalidUserError(AuthenticationError):
    """An error thrown when a username is invalid."""


def _require_string(string: str, name: str) -> str:
    """
    Check an argument is a non-whitespace only string.

    string - the string to check. Must be either falsy or a string.
    name - the name of the argument to use in exceptions.

    returns the stripped string.
    """
    if not string or not string.strip():
        raise ValueError(f"{name} is required")
    return string.strip()
