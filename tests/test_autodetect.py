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
    mappings = AutoDetectUtils._MAPPINGS
    assert mappings


def test_bad_filenames():
    """
    Test files that shouldn't get back a hit
    TODO: Maybe learn hypothesis and use it here
    """
    crappy_filenames = [" ", ".", ".txt", "fasta.txt", "><", ":=).=:"]

    for filename in crappy_filenames:
        possible_importers, prefix, suffix = AutoDetectUtils.determine_possible_importers(
            filename=filename
        )
        assert possible_importers is None
        assert prefix is filename
        assert suffix is None


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
            possible_importers, prefix, suffix = AutoDetectUtils.determine_possible_importers(
                filename=filename_variant
            )
            print("Testing", filename_variant, possible_importers)
            assert possible_importers is not None
            expected_suffix = filename_variant.split(".", heading_dotcount + 1)[-1]
            assert possible_importers == AutoDetectUtils._MAPPINGS["types"].get(
                expected_suffix.lower()), (suffix, filename_variant)
            assert suffix == expected_suffix
            assert prefix == filename_variant[:-len(expected_suffix) - 1]


def test_specific_filenames():
    """
    Test some made up filenames to check that multi-dot extensions are handled correctly
    """
    test_data = [
        ("filename", (None, "filename", None)),
        ("file.name", (None, "file.name", None)),
        ("fil.en.ame", (None, "fil.en.ame", None)),
        ("file.gZ", (
            [{
                'app_weight': 1,
                'id': 'decompress',
                'file_type': ['CompressedFileFormatArchive'],
            }],
            "file",
            "gZ"
            )
         ),
        ("file.name.gZ", (
            [{
                'app_weight': 1,
                'id': 'decompress',
                'file_type': ['CompressedFileFormatArchive'],
            }],
            "file.name",
            "gZ"
            )
         ),
        ("oscar_the_grouch_does_meth.FaStA.gz", (
            [
                {'app_weight': 1,
                 'id': 'assembly',
                 'file_type': ['FASTA']
                },
                {'app_weight': 1,
                 'id': 'gff_genome',
                 'file_type': ['FASTA']
                },
                {'app_weight': 1,
                 'id': 'gff_metagenome',
                 'file_type': ['FASTA']
                }
            ],
            "oscar_the_grouch_does_meth",
            "FaStA.gz",
            )
         ),
        ("look.at.all.these.frigging.dots.gff2.gzip", (
            [
                {'app_weight': 1,
                 'id': 'gff_genome',
                 'file_type': ['GFF']},
                {'app_weight': 1,
                 'id': 'gff_metagenome',
                 'file_type': ['GFF']
                }
            ],
            "look.at.all.these.frigging.dots",
            "gff2.gzip",
            )
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
    possible_importers, prefix, suffix = AutoDetectUtils.determine_possible_importers(
        filename=sra_file)
    assert possible_importers == [{'id': 'sra_reads', 'app_weight': 1, 'file_type': ['SRA']}]
    assert prefix == "test"
    assert suffix == "sra"


def test_zip_mappings():
    """
    Just testing a single app
    :return:
    """
    gz_file = "test.tar.gz"
    possible_importers, prefix, suffix = AutoDetectUtils.determine_possible_importers(
        filename=gz_file)
    assert possible_importers == [{
        'id': 'decompress',
        'app_weight': 1,
        'file_type': ['CompressedFileFormatArchive']
    }]
    assert prefix == "test"
    assert suffix == "tar.gz"


def test_get_mappings():
    """
    Basic test of the get mappings logic. Most of the logic is in determine_possible_importers
    which is throughly tested above.
    """
    assert AutoDetectUtils.get_mappings(["filename", "file.name.Gz", "some.dots.gff3.gz"]) == {
        "mappings": [
            None,
            [{
                'app_weight': 1,
                'id': 'decompress',
                'file_type': ['CompressedFileFormatArchive'],
            }],
            [
                {'app_weight': 1,
                 'id': 'gff_genome',
                 'file_type': ['GFF']},
                {'app_weight': 1,
                 'id': 'gff_metagenome',
                 'file_type': ['GFF']
                }
            ],
        ],
        "fileinfo": [
            {"prefix": "filename", "suffix": None},
            {"prefix": "file.name", "suffix": "Gz"},
            {"prefix": "some.dots", "suffix": "gff3.gz"},
        ]
    }
