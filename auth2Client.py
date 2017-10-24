'''
Created on Aug 1, 2016
A very basic KBase auth client for the Python server.
@author: gaprice@lbl.gov
modified for python3 and authV2
'''
import time as _time
import requests as _requests
import threading as _threading
import hashlib


class TokenCache(object):
    ''' A basic cache for tokens. '''

    _MAX_TIME_SEC = 5 * 60  # 5 min

    _lock = _threading.RLock()

    def __init__(self, maxsize=2000):
        self._cache = {}
        self._maxsize = maxsize
        self._halfmax = maxsize / 2  # int division to round down

    def get_user(self, token):
        token = hashlib.sha256(token.encode('utf8')).hexdigest()
        with self._lock:
            usertime = self._cache.get(token)
        if not usertime:
            return None

        user, intime = usertime
        if _time.time() - intime > self._MAX_TIME_SEC:
            return None
        return user

    def add_valid_token(self, token, user):
        if not token:
            raise ValueError('Must supply token')
        if not user:
            raise ValueError('Must supply user')
        token = hashlib.sha256(token.encode('utf8')).hexdigest()
        with self._lock:
            self._cache[token] = [user, _time.time()]
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

    _AUTH_URL = 'https://kbase.us/services/auth/api/V2/token'

    def __init__(self, auth_url=None):
        '''
        Constructor
        '''
        self._authurl = auth_url
        if not self._authurl:
            self._authurl = self._AUTH_URL
        self._cache = TokenCache()

    def get_user(self, token):
        if not token:
            raise ValueError('Must supply token')
        user = self._cache.get_user(token)
        if user:
            return user

        ret = _requests.get(self._authurl, headers={'Authorization': token})
        # ret = _requests.getpost(self._authurl, data=d)
        if not ret.ok:
            try:
                err = ret.json()
            except:
                ret.raise_for_status()
            raise ValueError('Error connecting to auth service: {} {}\n{}'
                             .format(ret.status_code, ret.reason,
                                     err['error']['message']))

        user = ret.json()['user']
        self._cache.add_valid_token(token, user)
        return user
