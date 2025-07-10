from configparser import ConfigParser, SectionProxy
from pathlib import Path

_AUTH_TOKEN = "AUTH_TOKEN"
_META_DIR = "META_DIR"
_DATA_DIR = "DATA_DIR"
_AUTH_URL = "AUTH_URL"
_CONCIERGE_PATH = "CONCIERGE_PATH"
_FILE_EXTENSION_MAPPINGS = "FILE_EXTENSION_MAPPINGS"
_DTS_MANIFEST_SCHEMA = "DTS_MANIFEST_SCHEMA"
_HEADING = "staging_service"


class StagingServiceConfig:
    """
    Constructs a simple config object from a passed config file path.
    This requires that all required values are present.
    See deployment/conf/deployment.cfg for an example.
    """

    def __init__(self, config_path: str):
        """
        Reads the INI-formatted config file at `config_path`.
        This expects a single section - staging_service.
        Any key that is missing or null will raise a ValueError.
        Raises a ValueError if the config_path is not provided.
        Raises a FileNotFoundError if config_path is not found.

        config_path: str - the path to the INI-formatted config file
        """
        if not config_path:
            raise ValueError("config_path is required")

        if not Path(config_path).exists():
            raise FileNotFoundError(f"Config path {config_path} does not exist")

        config = ConfigParser()
        config.read(config_path)

        if _HEADING not in config:
            raise ValueError(f"Config file {config_path} is missing required section {_HEADING}")

        heading = config[_HEADING]
        try:
            self.auth_url = _get_value(heading, _AUTH_URL)
            self.auth_token = _get_value(heading, _AUTH_TOKEN)
            self.data_dir = _get_path_value(heading, _DATA_DIR)
            self.meta_dir = _get_path_value(heading, _META_DIR)
            self.concierge_path = _get_path_value(heading, _CONCIERGE_PATH)
            self.file_extension_mappings = _get_path_value(heading, _FILE_EXTENSION_MAPPINGS)
            self.dts_manifest_schema = _get_path_value(heading, _DTS_MANIFEST_SCHEMA)
        except ValueError as err:
            # tack the file name on the error string
            raise ValueError(f"Config file {config_path} error: " + str(err))


def _get_value(section: SectionProxy, key: str) -> str:
    """
    Returns the value for a key in the given ConfigParser section.
    If the key or value isn't present, this raises a ValueError.
    """
    if key not in section:
        raise ValueError(f"missing required key {key} in section {section.name}")
    value = section.get(key)
    if not value:
        raise ValueError(
            f"required key {key} in section {section.name} must not be empty or all whitespace"
        )
    return value


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
