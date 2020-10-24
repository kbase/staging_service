import json

from typing import NamedTuple


class AutodetectConfigs(NamedTuple):
    supported_apps: dict
    extension_mappings: dict


class AutoDetectUtils:
    _FILE_EXTENSION_MAPPINGS = None  # expects to be set by config
    _MAPPINGS = None  # expects to be set by config

    # SUPPORTED_APPS = json.load(AVAILABLE_APPS_FP)
    # EXTENSION_MAPPINGS = json.load(EXTENSION_MAPPINGS_FP)

    @staticmethod
    def determine_possible_importers(filename):
        if "." in filename:
            suffix = filename.split(".")[-1].lower()
            return AutoDetectUtils._MAPPINGS["types"].get(suffix)
        else:
            return None

