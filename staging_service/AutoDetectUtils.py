from typing import NamedTuple
import json


class AutodetectConfigs(NamedTuple):
    supported_apps: dict
    extension_mappings: dict


class AutoDetectUtils:
    AVAILABLE_APPS_FP = "/Users/bsadkhin/workspace/staging_service/staging_service/autodetect/supported_apps.json"
    EXTENSION_MAPPINGS_FP = "/Users/bsadkhin/workspace/staging_service/staging_service/autodetect/extension_to_app.json"
    with open(AVAILABLE_APPS_FP) as f:
        SUPPORTED_APPS = json.load(f)

    with open(EXTENSION_MAPPINGS_FP) as f:
        EXTENSION_MAPPINGS = json.load(f)

    # SUPPORTED_APPS = json.load(AVAILABLE_APPS_FP)
    # EXTENSION_MAPPINGS = json.load(EXTENSION_MAPPINGS_FP)

    @staticmethod
    def determine_possible_importers(filename):
        if "." in filename:
            suffix = filename.split(".")[-1]

        else:
            return None

    @staticmethod
    def get_mappings(request):
        request = [
            "Genome1.fastq",
            "Genome2.fastq",
            "Genome3.fa",
            "Genome3.zip",
            "Genome3.cat" "Genome3",
        ]
        response = []
        for filename in request:
            response.append(AutoDetectUtils.determine_possible_importers(filename))
