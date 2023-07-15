"""
This class is in charge of determining possible importers by determining the suffix 
of the filepath pulled in, and by looking up the appropriate mappings in the 
supported_apps_w_extensions.json file
"""
from typing import Any, Dict, Optional, Tuple, Union

Mappings = dict[str, Any]

MappingsConfig = dict[str, Mappings]

# pylint: disable=C0115,C0116


class AutoDetectUtils:
    _MAPPINGS: Union[None, dict[str, Any]] = None  # expects to be set by config

    @classmethod
    def set_mappings(cls, mappings_config: MappingsConfig):
        cls._MAPPINGS = mappings_config["types"]

    @classmethod
    def has_mappings(cls) -> bool:
        if cls._MAPPINGS is not None:
            return True
        return False

    @classmethod
    def get_mappings_by_extension(cls, extension: str):
        if cls._MAPPINGS is not None:
            return cls._MAPPINGS.get(extension)

    @classmethod
    def get_extension_mappings(cls):
        return cls._MAPPINGS

    @classmethod
    def determine_possible_importers(
        cls,
        filename: str,
    ) -> Tuple[Optional[list], Dict[str, object]]:
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
        if dotcount and cls._MAPPINGS is not None:
            # preferentially choose the most specific suffix (e.g. longest)
            # to get file type mappings

            for i in range(1, dotcount + 1):
                parts = filename.split(".", i)
                suffix = parts[-1].lower()
                # pylint: disable=unsubscriptable-object
                # added because it complains about mappings below.
                if suffix in cls._MAPPINGS:  # pylint: disable=E1135
                    prefix = ".".join(parts[0:i])
                    return (
                        cls._MAPPINGS[suffix]["mappings"],
                        {
                            "prefix": prefix,
                            "suffix": parts[-1],
                            "file_ext_type": cls._MAPPINGS[suffix]["file_ext_type"],
                        },
                    )
        return None, {"prefix": filename, "suffix": None, "file_ext_type": []}

    @classmethod
    def get_mappings(cls, file_list: list) -> dict:
        """
        Given a list of files, get their mappings if they exist

        :param file_list: A list of files
        :return: return a listing of apps, a listing of extension_mappings for each filename,
            and information about each file, currently the file prefix and the suffix used to
            determine the mappings and a list of file types.
        """
        mappings = []
        fileinfo = []
        for filename in file_list:
            typemaps, file_importers = cls.determine_possible_importers(filename)
            mappings.append(typemaps)
            fileinfo.append(file_importers)
        return {
            "mappings": mappings,
            "fileinfo": fileinfo,
        }
