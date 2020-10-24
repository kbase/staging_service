import pytest
from staging_service.autodetect.GenerateMappings import type_to_extension_mapping
from staging_service.AutoDetectUtils import AutoDetectUtils
from staging_service.app import inject_config_dependencies
from tests.test_utils import bootstrap_config




@pytest.fixture(autouse=True)
def run_before_and_after_tests(tmpdir):
    config = bootstrap_config()
    inject_config_dependencies(config)


def test_config():
    """
    Test to make sure config injection is working for AutoDetectUtils
    #TODO Can test PATH injections as well
    :return:
    """
    mappings_fp = AutoDetectUtils._FILE_EXTENSION_MAPPINGS
    mappings = AutoDetectUtils._MAPPINGS
    assert mappings
    assert mappings_fp


def test_bad_filenames():
    """
    Test files that shouldn't get back a hit
    TODO: Maybe learn hypothesis and use it here
    """
    crappy_filenames = [" ", ".", ".txt", "fasta.txt", "><", ":=).=:"]

    for filename in crappy_filenames:
        possible_importers = AutoDetectUtils.determine_possible_importers(
            filename=filename
        )
        assert possible_importers is None


def test_reasonable_filenames():
    """
    Test variants "reasonable" filenames that are in the mappings
    Note: Some apps and mappings are not yet supported and are commented out
    """

    good_filenames = []
    for heading in type_to_extension_mapping.keys():
        extensions = type_to_extension_mapping[heading]
        for extension in extensions:
            good_filenames.append(f"{heading}.{extension}")

    for filename in good_filenames:
        for filename_variant in [
            filename,
            filename.upper(),
            filename.lower(),
            filename.title(),
        ]:
            possible_importers = AutoDetectUtils.determine_possible_importers(
                filename=filename_variant
            )
            assert possible_importers is not None
            suffix = filename_variant.split(".")[-1].lower()
            assert possible_importers == AutoDetectUtils._MAPPINGS["types"].get(suffix)

def test_sra_mappings():
    sra_file = "test.sra"
    possible_importers = AutoDetectUtils.determine_possible_importers(
        filename=sra_file
    )
    assert  AutoDetectUtils._MAPPINGS["apps"].get(suffix)