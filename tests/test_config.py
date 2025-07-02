import pytest
from pathlib import Path
from configparser import ConfigParser
from staging_service.config import StagingServiceConfig #, _get_value, _get_path_value

VALID_CONFIG = """
[staging_service]
AUTH_URL = https://example.com/auth
DATA_DIR = /kb/deployment/data
META_DIR = /kb/deployment/data/meta
CONCIERGE_PATH = /kb/deployment/concierge.json
FILE_EXTENSION_MAPPINGS = ./mappings.json
DTS_MANIFEST_SCHEMA = ./schema.json
"""

def write_config_file(config_dir: Path, content: str) -> str:
    # writes out some content to "config.cfg" in the provided
    # directory. Returns the path to the file as a string.
    file = config_dir / "config.cfg"
    file.write_text(content)
    return str(file)

def test_valid_config_parsing(tmp_path):
    config_path = write_config_file(tmp_path, VALID_CONFIG)
    config = StagingServiceConfig(config_path)

    assert config.auth_url == "https://example.com/auth"
    assert Path(config.data_dir).is_absolute()
    assert config.data_dir.endswith("data")
    assert config.meta_dir.endswith("meta")

def test_missing_config_path():
    with pytest.raises(ValueError, match="config_path is required"):
        StagingServiceConfig("")

def test_nonexistent_config_file():
    with pytest.raises(FileNotFoundError):
        StagingServiceConfig("nonexistent.ini")

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

def test_relative_path_resolution(tmp_path, monkeypatch):
    config = ConfigParser()
    config.add_section("staging_service")
    config.set("staging_service", "DATA_DIR", "./relative_dir")
    monkeypatch.chdir(tmp_path)
    path = _get_path_value(config["staging_service"], "DATA_DIR")
    assert Path(path) == tmp_path / "relative_dir"
