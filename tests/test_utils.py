import configparser
import os
import traceback
from pathlib import Path
from typing import Any

import openpyxl
from dotenv import load_dotenv


def bootstrap():
    test_env_0 = "../test.env"
    test_env_1 = "test.env"
    test_env_2 = "test/test.env"

    for item in [test_env_0, test_env_1, test_env_2]:
        try:
            load_dotenv(item, verbose=True)
        except Exception:
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
    assert isinstance(got, type(expected))


def check_file_contents(file: Path, lines: list[str]):
    with open(file, "r", encoding="utf-8") as f:
        assert f.readlines() == lines


def check_excel_contents(
    workbook: openpyxl.Workbook,
    sheetname: str,
    contents: list[list[Any]],
    column_widths: list[int],
):
    sheet = workbook[sheetname]
    for i, row in enumerate(sheet.iter_rows()):
        assert [cell.value for cell in row] == contents[i]
    # presumably there's an easier way to do this, but it works so f it
    dims = [sheet.column_dimensions[dim].width for dim in sheet.column_dimensions]
    assert dims == column_widths
