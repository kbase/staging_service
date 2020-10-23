from staging_service.AutoDetectUtils import AutoDetectUtils
from staging_service.app import inject_config_dependencies
from tests.test_utils import bootstrap_config

config = bootstrap_config()


def test_config():
    """
    Test to make sure config injection is working for AutoDetectUtils
    #TODO Can test PATH injections as well
    :return:
    """
    mappings_fp = AutoDetectUtils._FILE_EXTENSION_MAPPINGS
    mappings = AutoDetectUtils._MAPPINGS
    assert mappings is None
    assert mappings_fp is None
    inject_config_dependencies(config)

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
    Test "reasonable" filenames that defintely are in the mapping
    #TODO Change this to test all extensions
    """
    good_filenames = [
        "fasta.fasta",
        "fasta.fastq",
        "fork.fa",
        "bog.sra",
        "gff.gff3",
        "gff.gff",
    ]

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
            print("looking for ", suffix)
            assert possible_importers == AutoDetectUtils._MAPPINGS["types"].get(suffix)
