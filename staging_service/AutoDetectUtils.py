"""
This class is in charge of determining possible importers by determining the suffix of the filepath pulled in,
and by looking up the appropriate mappings in the supported_apps_w_extensions.json file
"""
from typing import Optional, Tuple


class AutoDetectUtils:
    _MAPPINGS = None  # expects to be set by config

    @staticmethod
    def determine_possible_importers(filename: str) -> Tuple[Optional[list], str, Optional[str]]:
        """
        Given a filename, come up with a reference to all possible apps.
        :param filename: The filename to find applicable apps for
        :return: A tuple containing:
            a list of mapping references, or None if not found
            the file prefix
            the file suffix, if a suffix matched a mapping
        """
        dotcount = filename.count(".")
        if dotcount:
            # preferentially choose the most specific suffix (e.g. longest)
            # to get file type mappings
            for i in range(1, dotcount + 1):
                parts = filename.split(".", i)
                suffix = parts[-1].lower()
                if suffix in AutoDetectUtils._MAPPINGS["types"]:
                    prefix = ".".join(parts[0:i])
                    return AutoDetectUtils._MAPPINGS["types"][suffix], prefix, parts[-1]
        return None, filename, None

    @staticmethod
    def get_mappings(file_list: list) -> dict:
        """
        Given a list of files, get their mappings if they exist
        :param file_list: A list of files
        :return: return a listing of apps, a listing of extension_mappings for each filename,
            and information about each file, currently the file prefix and the suffix used to
            determine the mappings
        """
        mappings = []
        fileinfo = []
        for filename in file_list:
            typemaps, prefix, suffix = AutoDetectUtils.determine_possible_importers(filename)
            mappings.append(typemaps)
            fileinfo.append({"prefix": prefix, "suffix": suffix})
        rv = {
            "mappings": mappings,
            "fileinfo": fileinfo,
        }
        return rv
