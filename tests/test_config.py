import pytest
from pathlib import Path
from staging_service.config import MissingAuthToken, StagingServiceConfig
import os

# separate these for easier assertions
AUTH_URL = "https://example.com/auth"
DATA_DIR = "/kb/deployment/data/bulk"
META_DIR = "/kb/deployment/data/metadata"
CONCIERGE_PATH = "/kbaseconcierge"
FILE_EXTENSION_MAPPINGS = "/kb/deployment/file_mappings.json"
DTS_MANIFEST_SCHEMA = "/kb/deployment/dts_manifest_schema.json"

VALID_CONFIG = f"""
[staging_service]
AUTH_URL = {AUTH_URL}
DATA_DIR = {DATA_DIR}
META_DIR = {META_DIR}
CONCIERGE_PATH = {CONCIERGE_PATH}
FILE_EXTENSION_MAPPINGS = {FILE_EXTENSION_MAPPINGS}
DTS_MANIFEST_SCHEMA = {DTS_MANIFEST_SCHEMA}
"""


def write_config_file(config_dir: Path, content: str) -> str:
    """
    Writes out some content to "config.cfg" in the provided
    directory. Returns the path to the file as a string.
    """
    file = config_dir / "config.cfg"
    file.write_text(content)
    return str(file)


def test_valid_config(tmp_path):
    config_path = write_config_file(tmp_path, VALID_CONFIG)
    config = StagingServiceConfig(config_path)

    assert config.auth_url == AUTH_URL
    assert config.data_dir == DATA_DIR
    assert config.meta_dir == META_DIR
    assert config.concierge_path == CONCIERGE_PATH
    assert config.file_extension_mappings == FILE_EXTENSION_MAPPINGS
    assert config.dts_manifest_schema == DTS_MANIFEST_SCHEMA
    assert config.auth_token == os.environ["AUTH_TOKEN"]


def test_missing_config_path():
    with pytest.raises(ValueError, match="config_path is required"):
        StagingServiceConfig("")


def test_missing_config_file():
    with pytest.raises(FileNotFoundError):
        StagingServiceConfig("missing.cfg")


def test_missing_heading(tmp_path):
    bad_config = "[wrong_section]\nfoo=bar"
    config_path = write_config_file(tmp_path, bad_config)
    with pytest.raises(ValueError, match="missing required section"):
        StagingServiceConfig(config_path)


def test_missing_required_key(tmp_path):
    bad_config = "[staging_service]\nDATA_DIR=./data"
    config_path = write_config_file(tmp_path, bad_config)
    with pytest.raises(ValueError, match="Please provide AUTH_URL"):
        StagingServiceConfig(config_path)


def test_path_resolution(tmp_path):
    non_relative_config = f"""
        [staging_service]
        AUTH_URL = {AUTH_URL}
        DATA_DIR = ./data
        META_DIR = ./meta
        CONCIERGE_PATH = ./concierge
        FILE_EXTENSION_MAPPINGS = ./file_extension_mappings.json
        DTS_MANIFEST_SCHEMA = ./dts_manifest_schema.json
    """
    config_path = write_config_file(tmp_path, non_relative_config)
    config = StagingServiceConfig(config_path)
    config_keys = [
        "data_dir",
        "meta_dir",
        "concierge_path",
        "file_extension_mappings",
        "dts_manifest_schema",
    ]
    for key in config_keys:
        value = getattr(config, key)
        assert Path(value).is_absolute()


def test_missing_auth_token(monkeypatch, tmp_path):
    monkeypatch.delenv("AUTH_TOKEN")
    config_path = write_config_file(tmp_path, VALID_CONFIG)
    with pytest.raises(MissingAuthToken, match="AUTH_TOKEN environment variable must be provided"):
        StagingServiceConfig(config_path)
