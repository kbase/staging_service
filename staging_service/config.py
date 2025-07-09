from configparser import ConfigParser, SectionProxy
import os
from pathlib import Path

_ENV_AUTH_TOKEN = "AUTH_TOKEN"
_META_DIR = "META_DIR"
_DATA_DIR = "DATA_DIR"
_AUTH_URL = "AUTH_URL"
_CONCIERGE_PATH = "CONCIERGE_PATH"
_FILE_EXTENSION_MAPPINGS = "FILE_EXTENSION_MAPPINGS"
_DTS_MANIFEST_SCHEMA = "DTS_MANIFEST_SCHEMA"
_HEADING = "staging_service"
_TEST_TOKEN = "TEST_TOKEN"
_TEST_USER = "TEST_USER"


class StagingServiceConfig:
    """
    Constructs a simple config object from a passed config file path.
    This requires that all values are present.
    See deployment/conf/deployment.cfg for an example.
    It also holds the service auth token from the AUTH_TOKEN environment variable.
    TODO: update when AUTH_TOKEN is moved into the config - see issue #227
    """

    def __init__(self, config_path: str):
        if not config_path:
            raise ValueError("config_path is required")

        if not Path(config_path).exists():
            raise FileNotFoundError(f"Config path {config_path} does not exist")

        config = ConfigParser()
        config.read(config_path)

        if _HEADING not in config:
            raise ValueError(f"Config file {config_path} is missing required section {_HEADING}")

        if _ENV_AUTH_TOKEN not in os.environ or not os.environ[_ENV_AUTH_TOKEN]:
            raise MissingAuthToken("AUTH_TOKEN environment variable must be provided")
        self.auth_token = os.environ[_ENV_AUTH_TOKEN]

        heading = config[_HEADING]
        try:
            self.auth_url = _get_value(heading, _AUTH_URL)
            self.data_dir = _get_path_value(heading, _DATA_DIR)
            self.meta_dir = _get_path_value(heading, _META_DIR)
            self.concierge_path = _get_path_value(heading, _CONCIERGE_PATH)
            self.file_extension_mappings = _get_path_value(heading, _FILE_EXTENSION_MAPPINGS)
            self.dts_manifest_schema = _get_path_value(heading, _DTS_MANIFEST_SCHEMA)
        except ValueError as err:
            # tack the file name on the error string
            raise ValueError(f"Config file {config_path} error: " + str(err))
        self.test_token = _get_value(heading, _TEST_TOKEN, is_required=False)
        self.test_user = _get_value(heading, _TEST_USER, is_required=False)


def _get_value(section: SectionProxy, key: str, is_required: bool = True) -> str | None:
    """
    Returns the value for a key in the given ConfigParser section.
    If is_required is True, and the value isn't present, this raises a ValueError.
    If is_required is False, and the value isn't present, this returns None.
    """
    if key not in section and is_required:
        raise ValueError(f"missing required key {key} in section {section.name}")
    return section.get(key)


def _get_path_value(section: SectionProxy, key: str) -> str:
    """
    Returns a value for a key that's expected to be a file path. This resolves the path and makes
    it absolute. I.e. a path like ./foo becomes /path/to/local/dir/foo
    TODO: This returns paths as strings, not Path-like objects, as much of the rest of the service
    expects them that way. Consider changing it later.
    """
    return str(Path(_get_value(section, key)).absolute().resolve())


class MissingAuthToken(Exception):
    """Should be raised if the auth token environment variable is missing or empty"""
