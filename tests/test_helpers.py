import configparser
import os
import shutil
import traceback
from pathlib import Path
from typing import Any

import openpyxl
from dotenv import load_dotenv

test_config = configparser.ConfigParser()
test_config.read(os.environ["KB_DEPLOYMENT_CONFIG"])

DATA_DIR = test_config["staging_service"]["DATA_DIR"]
META_DIR = test_config["staging_service"]["META_DIR"]
AUTH_URL = test_config["staging_service"]["AUTH_URL"]
if DATA_DIR.startswith("."):
    DATA_DIR = os.path.normpath(os.path.join(os.getcwd(), DATA_DIR))
if META_DIR.startswith("."):
    META_DIR = os.path.normpath(os.path.join(os.getcwd(), META_DIR))


def bootstrap():
    """
    Attempts to load environment variables from a number of potentially
    present files

    Not sure it actually does anything useful.
    """
    test_env_0 = "../test.env"
    test_env_1 = "test.env"
    test_env_2 = "test/test.env"

    for potential_env_file in [test_env_0, test_env_1, test_env_2]:
        try:
            load_dotenv(potential_env_file, verbose=True)
        except IOError:
            pass


def bootstrap_config():
    bootstrap()
    config_filepath = os.environ["KB_DEPLOYMENT_CONFIG"]
    if not os.path.exists(config_filepath):
        raise FileNotFoundError(config_filepath)

    config = configparser.ConfigParser()
    config.read(config_filepath)
    return config


def assert_exception_correct(got: Exception, expected: Exception):
    err = "".join(traceback.TracebackException.from_exception(got).format())
    assert got.args == expected.args, err
    assert type(got) == type(expected)


def assert_file_contents(file: Path, lines: list[str]):
    with open(file, "r", encoding="utf-8") as f:
        assert f.readlines() == lines


def check_excel_contents(
    wb: openpyxl.Workbook,
    sheetname: str,
    contents: list[list[Any]],
    column_widths: list[int],
):
    sheet = wb[sheetname]
    for i, row in enumerate(sheet.iter_rows()):
        assert [cell.value for cell in row] == contents[i]
    # presumably there's an easier way to do this, but it works so f it
    dims = [sheet.column_dimensions[dim].width for dim in sheet.column_dimensions]
    assert dims == column_widths


class FileUtil:
    def __init__(self, base_dir=DATA_DIR):
        self.base_dir = base_dir

    def __enter__(self):
        os.makedirs(self.base_dir, exist_ok=True)
        shutil.rmtree(self.base_dir)
        os.makedirs(self.base_dir, exist_ok=False)
        return self

    def __exit__(self, *args):
        shutil.rmtree(self.base_dir)

    def make_file(self, path, contents):
        path = os.path.join(self.base_dir, path)
        with open(path, encoding="utf-8", mode="w") as f:
            f.write(contents)
        return path

    def make_dir(self, path):
        path = os.path.join(self.base_dir, path)
        os.makedirs(path, exist_ok=True)
        return path

    def remove_dir(self, path):
        shutil.rmtree(path)
