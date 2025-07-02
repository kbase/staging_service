from configparser import ConfigParser, SectionProxy
import os
from pathlib import Path

_META_DIR = "META_DIR"
_DATA_DIR = "DATA_DIR"
_AUTH_URL = "AUTH_URL"
_CONCIERGE_PATH = "CONCIERGE_PATH"
_FILE_EXTENSION_MAPPINGS = "FILE_EXTENSION_MAPPINGS"
_DTS_MANIFEST_SCHEMA = "DTS_MANIFEST_SCHEMA"
_HEADING = "staging_service"

class StagingServiceConfig:
    def __init__(self, config_path: str):
        if not config_path:
            raise ValueError("config_path is required")

        if not Path(config_path).exists():
            raise FileNotFoundError(f"config path {config_path} does not exist")

        config = ConfigParser()
        config.read(config_path)

        if _HEADING not in config:
            raise ValueError(f"config file {config_path} is missing required section {_HEADING}")

        heading = config[_HEADING]
        self.auth_url = _get_value(heading, _AUTH_URL)
        self.data_dir = _get_path_value(heading, _DATA_DIR)
        self.meta_dir = _get_path_value(heading, _META_DIR)
        self.concierge_path = _get_path_value(heading, _CONCIERGE_PATH)
        self.file_extension_mappings = _get_path_value(heading, _FILE_EXTENSION_MAPPINGS)
        self.dts_manifest_schema = _get_path_value(heading, _DTS_MANIFEST_SCHEMA)


def _get_value(section: SectionProxy, key: str, required: bool = True) -> str | None:
    if key not in section and required:
        raise ValueError(f"Please provide {key} in the config file section {section.name}")
    return section.get(key)

def _get_path_value(section, key, required: bool = True) -> str | None:
    value = _get_value(section, key, required=required)
    if value is not None and value.startswith("."):
        value = os.path.normpath(os.path.join(os.getcwd(), value))
    return value
