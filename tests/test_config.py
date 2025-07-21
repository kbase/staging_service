import pytest
from pathlib import Path
from staging_service.config import StagingServiceConfig

# separate these for easier assertions
AUTH_URL = "https://example.com/auth"
DATA_DIR = "/kb/deployment/data/bulk"
META_DIR = "/kb/deployment/data/metadata"
CONCIERGE_PATH = "/kbaseconcierge"
FILE_EXTENSION_MAPPINGS = "/kb/deployment/file_mappings.json"
DTS_MANIFEST_SCHEMA = "/kb/deployment/dts_manifest_schema.json"
AUTH_TOKEN = "fake_auth_token"
DTS_STAGING_DIR = "/kb/deployment/data/dts"
WATCH_DTS_FILES = "true"

VALID_HEADER_NAME = "staging_service"
VALID_HEADER = f"[{VALID_HEADER_NAME}]"

DEFAULT_CONFIG_DICT = {
    "AUTH_URL": AUTH_URL,
    "DATA_DIR": DATA_DIR,
    "META_DIR": META_DIR,
    "DTS_STAGING_DIR": DTS_STAGING_DIR,
    "CONCIERGE_PATH": CONCIERGE_PATH,
    "FILE_EXTENSION_MAPPINGS": FILE_EXTENSION_MAPPINGS,
    "DTS_MANIFEST_SCHEMA": DTS_MANIFEST_SCHEMA,
    "AUTH_TOKEN": AUTH_TOKEN,
    "WATCH_DTS_FILES": WATCH_DTS_FILES,
}


def dummy_config(header: str, config_dict: dict[str, str]) -> str:
    return header + "\n" + "\n".join([f"{k} = {v}" for k, v in config_dict.items()])


def write_config_file(config_dir: Path, content: str) -> str:
    """
    Writes out some content to "config.cfg" in the provided
    directory. Returns the path to the file as a string.
    """
    file = config_dir / "config.cfg"
    file.write_text(content)
    return str(file)


def validate_config(config: StagingServiceConfig, **kwargs):
    """
    Not the prettiest validator, but avoids a zillion kwargs.
    This validates that each attribute in the config file is as expected.
    Default values are given in DEFAULT_CONFIG_DICT above.
    These can be updated to your use case by changing the relevant kwarg.
    See test_valid_config_with_test_info for an example.
    """
    config_attrs = [
        "auth_url",
        "data_dir",
        "meta_dir",
        "concierge_path",
        "file_extension_mappings",
        "dts_manifest_schema",
        "auth_token",
        "dts_staging_dir",
    ]
    config_values = {key.lower(): value for key, value in DEFAULT_CONFIG_DICT.items()}
    config_values = config_values | kwargs
    for attr in config_attrs:
        assert getattr(config, attr) == config_values[attr]


def test_valid_config(tmp_path):
    config_path = write_config_file(tmp_path, dummy_config(VALID_HEADER, DEFAULT_CONFIG_DICT))
    config = StagingServiceConfig(config_path)
    validate_config(config)


def test_missing_config_path():
    with pytest.raises(ValueError, match="config_path is required"):
        StagingServiceConfig("")


def test_missing_config_file():
    missing_file = "missing.cfg"
    with pytest.raises(FileNotFoundError, match=f"Config path {missing_file} does not exist"):
        StagingServiceConfig(missing_file)


def test_missing_heading(tmp_path):
    bad_config = "[wrong_section]\nfoo=bar"
    config_path = write_config_file(tmp_path, bad_config)
    with pytest.raises(
        ValueError,
        match=f"Config file {config_path} is missing required section {VALID_HEADER_NAME}",
    ):
        StagingServiceConfig(config_path)


@pytest.mark.parametrize("missing_key", DEFAULT_CONFIG_DICT.keys())
def test_missing_required_key(tmp_path, missing_key):
    missing_config_dict = DEFAULT_CONFIG_DICT.copy()
    del missing_config_dict[missing_key]
    config_path = write_config_file(tmp_path, dummy_config(VALID_HEADER, missing_config_dict))
    with pytest.raises(
        ValueError,
        match=f"Config file {config_path} error: missing required key {missing_key} in section {VALID_HEADER_NAME}",
    ):
        StagingServiceConfig(config_path)


@pytest.mark.parametrize("whitespace_key", DEFAULT_CONFIG_DICT.keys())
def test_whitespace_required_key(tmp_path, whitespace_key):
    whitespace_config_dict = DEFAULT_CONFIG_DICT.copy()
    whitespace_config_dict[whitespace_key] = "   "
    config_path = write_config_file(tmp_path, dummy_config(VALID_HEADER, whitespace_config_dict))
    with pytest.raises(
        ValueError,
        match=f"Config file {config_path} error: required key {whitespace_key} in section {VALID_HEADER_NAME} must not be empty or all whitespace",
    ):
        StagingServiceConfig(config_path)


def test_path_resolution(tmp_path):
    non_relative_config = f"""
        [staging_service]
        AUTH_URL = {AUTH_URL}
        AUTH_TOKEN = {AUTH_TOKEN}
        DATA_DIR = ./data
        META_DIR = ./meta
        CONCIERGE_PATH = ./concierge
        FILE_EXTENSION_MAPPINGS = ./file_extension_mappings.json
        DTS_MANIFEST_SCHEMA = ./dts_manifest_schema.json
        DTS_STAGING_DIR = ./data/dts
        WATCH_DTS_FILES = {WATCH_DTS_FILES}
    """
    config_path = write_config_file(tmp_path, non_relative_config)
    config = StagingServiceConfig(config_path)
    config_keys = [
        "data_dir",
        "meta_dir",
        "concierge_path",
        "file_extension_mappings",
        "dts_manifest_schema",
        "dts_staging_dir",
    ]
    for key in config_keys:
        value = getattr(config, key)
        assert Path(value).is_absolute()
