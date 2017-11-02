'''
Created on Aug 1, 2016
A very basic KBase auth client for the Python server.
@author: gaprice@lbl.gov
modified for python3 and authV2
'''
import time as _time
import aiohttp
import hashlib


class TokenCache(object):
    ''' A basic cache for tokens. '''

    _MAX_TIME_SEC = 5 * 60  # 5 min

    def __init__(self, maxsize=2000):
        self._cache = {}
        self._maxsize = maxsize
        self._halfmax = maxsize / 2  # int division to round down

    def get_user(self, token):
        token = hashlib.sha256(token.encode('utf8')).hexdigest()
        usertime = self._cache.get(token)
        if not usertime:
            return None

        user, intime, expire_time = usertime
        now = _time.time()
        if now - intime > self._MAX_TIME_SEC or now > expire_time:
            return None
        return user

    def add_valid_token(self, token, user, expire_time):
        if not token:
            raise aiohttp.web.HTTPBadRequest(text='Must supply token')
        if not user:
            raise aiohttp.web.HTTPBadRequest(text='Must supply user')
        token = hashlib.sha256(token.encode('utf8')).hexdigest()
        self._cache[token] = [user, _time.time(), expire_time]
        if len(self._cache) > self._maxsize:
            for i, (t, _) in enumerate(sorted(self._cache.items(),
                                              key=lambda v: v[1][1])):
                if i <= self._halfmax:
                    del self._cache[t]
                else:
                    break


class KBaseAuth2(object):
    '''
    A very basic KBase auth client for the Python server.
    '''

    _AUTH_URL = 'https://ci.kbase.us/services/auth/api/V2/token'
    # TODO config this up

    def __init__(self, auth_url=None):
        '''
        Constructor
        '''
        self._authurl = auth_url
        if not self._authurl:
            self._authurl = self._AUTH_URL
        self._cache = TokenCache()

    async def get_user(self, token):
        if not token:
            raise aiohttp.web.HTTPBadRequest(text='Must supply token')
        user = self._cache.get_user(token)
        if user:
            return user
        # TODO this part should not be blocking and should await the auth server
        async with aiohttp.ClientSession() as session:
            async with session.get(self._authurl, headers={'Authorization': token}) as resp:
                ret = await resp.json()
                if not resp.reason == 'OK':
                    try:
                        err = ret.json()
                    except:
                        ret.raise_for_status()  # TODO check that this works
                    raise aiohttp.web.HTTPUnauthorized(
                        text='Error connecting to auth service: {} {}\n{}'
                        .format(ret['error']['httpcode'], resp.reason,
                                err['error']['message']))
        # whichever one comes first
        self._cache._MAX_TIME_SEC = ret['cachefor']
        self._cache.add_valid_token(token, ret['user'], ret['expires'])
        return ret['user']
