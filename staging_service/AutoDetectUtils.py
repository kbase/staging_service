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
        Given a filename, come up with a reference to all possible apps.
        :param filename: The filename to find applicable apps for
        :return: A list of mapping references, or None if not found
        """
        dotcount = filename.count(".")
        if dotcount:
            # preferentially choose the most specific suffix (e.g. longest)
            # to get file type mappings
            for i in range(1, dotcount + 1):
                suffix = filename.split(".", i)[-1].lower()
                if suffix in AutoDetectUtils._MAPPINGS["types"]:
                    return AutoDetectUtils._MAPPINGS["types"][suffix]
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
