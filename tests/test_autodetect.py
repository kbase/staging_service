import pytest
from staging_service.autodetect.GenerateMappings import file_format_to_extension_mapping
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
    for heading in file_format_to_extension_mapping.keys():
        extensions = file_format_to_extension_mapping[heading]
        for extension in extensions:
            good_filenames.append((f"{heading}.{extension}", heading.count(".")))

    for filename, heading_dotcount in good_filenames:
        for filename_variant in [
            filename,
            filename.upper(),
            filename.lower(),
            filename.title(),
        ]:
            possible_importers = AutoDetectUtils.determine_possible_importers(
                filename=filename_variant
            )
            print("Testing", filename_variant, possible_importers)
            assert possible_importers is not None
            suffix = filename_variant.split(".", heading_dotcount + 1)[-1].lower()
            assert possible_importers == AutoDetectUtils._MAPPINGS["types"].get(suffix), (
                suffix, filename_variant)


def test_specific_filenames():
    """
    Test some made up filenames to check that multi-dot extensions are handled correctly
    """
    test_data = [
        ("filename", None),
        ("file.name", None),
        ("fil.en.ame", None),
        ("file.gZ", [{
            'app_weight': 1,
            'id': 'decompress',
            'title': 'Decompress/Unpack',
            'file_type': ['CompressedFileFormatArchive'],
            }]
         ),
        ("file.name.gZ", [{
            'app_weight': 1,
            'id': 'decompress',
            'title': 'Decompress/Unpack',
            'file_type': ['CompressedFileFormatArchive'],
            }]
         ),
        ("oscar_the_grouch_does_meth.FaStA.gz", [
            {'app_weight': 1,
             'id': 'assembly',
             'title': 'Assembly',
             'file_type': ['FASTA']
             },
            {'app_weight': 1,
             'id': 'gff_genome',
             'title': 'GFF/FASTA Genome',
             'file_type': ['FASTA']
             },
            {'app_weight': 1,
             'id': 'gff_metagenome',
             'title': 'GFF/FASTA MetaGenome',
             'file_type': ['FASTA']
             }
            ]
         ),
        ("look.at.all.these.frigging.dots.gff2.gzip", [
            {'app_weight': 1,
             'id': 'gff_genome',
             'title': 'GFF/FASTA Genome',
             'file_type': ['GFF']},
            {'app_weight': 1,
             'id': 'gff_metagenome',
             'title': 'GFF/FASTA MetaGenome',
             'file_type': ['GFF']}
            ]
         )
    ]

    for filename, importers in test_data:
        assert AutoDetectUtils.determine_possible_importers(filename) == importers, filename


def test_sra_mappings():
    """
    Just testing a single app
    :return:
    """
    sra_file = "test.sra"
    possible_importers = AutoDetectUtils.determine_possible_importers(filename=sra_file)
    app_title = "SRA Reads"
    possible_app = possible_importers[0]["title"]
    mappings = AutoDetectUtils._MAPPINGS
    assert mappings["apps"][possible_app] == mappings["apps"][app_title]


def test_zip_mappings():
    """
    Just testing a single app
    :return:
    """
    gz_file = "test.tar.gz"
    possible_importers = AutoDetectUtils.determine_possible_importers(filename=gz_file)
    app_title = "Decompress/Unpack"
    possible_app = possible_importers[0]["title"]
    mappings = AutoDetectUtils._MAPPINGS
    assert mappings["apps"][possible_app] == mappings["apps"][app_title]
