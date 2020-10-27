"""
This class is in charge of determining possible importers by determining the suffix of the filepath pulled in,
and by looking up the appropriate mappings in the supported_apps_w_extensions.json file
"""
from typing import Optional


class AutoDetectUtils:
    _FILE_EXTENSION_MAPPINGS = None  # expects to be set by config
    _MAPPINGS = None  # expects to be set by config

    @staticmethod
    def determine_possible_importers(filename: str) -> Optional[list]:
        """
        Given a filename, come up with a reference to all possible apps
        :param filename: The filename to find applicable apps for
        :return: A list of mapping references, or None if not found
        """
        if "." in filename:
            suffix = filename.split(".")[-1].lower()
            return AutoDetectUtils._MAPPINGS["types"].get(suffix)
        else:
            return None

    @staticmethod
    def get_mappings(file_list: list) -> dict:
        """
        Given a list of files, get their mappings if they exist
        :param file_list: A list of files 
        :return: return a listing of apps and a listing of extension_mappings for each filename
        """
        mappings = []
        for filename in file_list:
            mappings.append(AutoDetectUtils.determine_possible_importers(filename))
        rv = {"apps": AutoDetectUtils._MAPPINGS["apps"], "mappings": mappings}
        return rv
