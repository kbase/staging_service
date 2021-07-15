"""
This class is in charge of determining possible importers by determining the suffix of the filepath pulled in,
and by looking up the appropriate mappings in the supported_apps_w_extensions.json file
"""
from typing import Optional, Tuple, Dict


class AutoDetectUtils:
    _MAPPINGS = None  # expects to be set by config

    @staticmethod
    def determine_possible_importers(filename: str) -> Tuple[Optional[list], Dict[str, object]]:
        """
        Given a filename, come up with a reference to all possible apps.
        :param filename: The filename to find applicable apps for
        :return: A tuple containing:
            a list of mapping references, or None if not found
            The fileinfo dict, containing:
                the file prefix
                the file suffix, if a suffix matched a mapping
                the file types, if a suffix matched a mapping, otherwise an empty list 
        """
        dotcount = filename.count(".")
        if dotcount:
            # preferentially choose the most specific suffix (e.g. longest)
            # to get file type mappings
            m = AutoDetectUtils._MAPPINGS
            for i in range(1, dotcount + 1):
                parts = filename.split(".", i)
                suffix = parts[-1].lower()
                if suffix in m["types"]:
                    prefix = ".".join(parts[0:i])
                    return (
                        m["types"][suffix]["mappings"],
                        {"prefix": prefix,
                         "suffix": parts[-1],
                         "file_ext_type": m["types"][suffix]["file_ext_type"],
                        }
                    )
        return None, {"prefix": filename, "suffix": None, "file_ext_type": []}

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
            typemaps, fi = AutoDetectUtils.determine_possible_importers(filename)
            mappings.append(typemaps)
            fileinfo.append(fi)
        rv = {
            "mappings": mappings,
            "fileinfo": fileinfo,
        }
        return rv
