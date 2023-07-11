import pytest

from staging_service.app import inject_config_dependencies
from staging_service.autodetect.GenerateMappings import extensions_mapping
from staging_service.autodetect.Mappings import file_format_to_extension_mapping
from staging_service.AutoDetectUtils import AutoDetectUtils
from tests.test_utils import bootstrap_config


@pytest.fixture(autouse=True, scope="module")
def run_before_tests():
    config = bootstrap_config()
    inject_config_dependencies(config)


def test_config():
    """
    Test to make sure config injection is working for AutoDetectUtils
    #TODO Can test PATH injections as well
    :return:
    """
    mappings = AutoDetectUtils.has_mappings()
    assert mappings


def test_bad_filenames():
    """
    Test files that shouldn't get back a hit
    TODO: Maybe learn hypothesis and use it here
    """
    crappy_filenames = [" ", ".", ".txt", "fasta.txt", "><", ":=).=:"]

    for filename in crappy_filenames:
        possible_importers, fileinfo = AutoDetectUtils.determine_possible_importers(
            filename=filename
        )
        assert possible_importers is None
        assert fileinfo == {"prefix": filename, "suffix": None, "file_ext_type": []}


def test_reasonable_filenames():
    """
    Test variants "reasonable" filenames that are in the mappings
    Note: Some apps and mappings are not yet supported and are commented out
    """

    good_filenames = []
    for heading, extensions in file_format_to_extension_mapping.items():
        for extension in extensions:
            good_filenames.append(
                (
                    f"{heading}.{extension}",
                    heading.count("."),
                    extensions_mapping[extension]["file_ext_type"],
                )
            )

    for filename, heading_dotcount, ext in good_filenames:
        for filename_variant in [
            filename,
            filename.upper(),
            filename.lower(),
            filename.title(),
        ]:
            possible_importers, fileinfo = AutoDetectUtils.determine_possible_importers(
                filename=filename_variant
            )
            assert possible_importers is not None
            expected_suffix = filename_variant.split(".", heading_dotcount + 1)[-1]
            assert (
                possible_importers
                == AutoDetectUtils.get_mappings_by_extension(expected_suffix.lower())[
                    "mappings"
                ]
            ), filename_variant
            assert fileinfo == {
                "prefix": filename_variant[: -len(expected_suffix) - 1],
                "suffix": expected_suffix,
                "file_ext_type": ext,
            }


def test_specific_filenames():
    """
    Test some made up filenames to check that multi-dot extensions are handled correctly
    """
    test_data = [
        (
            "filename",
            (None, {"prefix": "filename", "suffix": None, "file_ext_type": []}),
        ),
        (
            "file.name",
            (None, {"prefix": "file.name", "suffix": None, "file_ext_type": []}),
        ),
        (
            "fil.en.ame",
            (None, {"prefix": "fil.en.ame", "suffix": None, "file_ext_type": []}),
        ),
        (
            "file.gZ",
            (
                [
                    {
                        "app_weight": 1,
                        "id": "decompress",
                        "title": "Decompress/Unpack",
                    }
                ],
                {
                    "prefix": "file",
                    "suffix": "gZ",
                    "file_ext_type": ["CompressedFileFormatArchive"],
                },
            ),
        ),
        (
            "file.name.gZ",
            (
                [
                    {
                        "app_weight": 1,
                        "id": "decompress",
                        "title": "Decompress/Unpack",
                    }
                ],
                {
                    "prefix": "file.name",
                    "suffix": "gZ",
                    "file_ext_type": ["CompressedFileFormatArchive"],
                },
            ),
        ),
        (
            "oscar_the_grouch_does_meth.FaStA.gz",
            (
                [
                    {
                        "app_weight": 1,
                        "id": "assembly",
                        "title": "Assembly",
                    },
                    {
                        "app_weight": 1,
                        "id": "gff_genome",
                        "title": "GFF/FASTA Genome",
                    },
                    {
                        "app_weight": 1,
                        "id": "gff_metagenome",
                        "title": "GFF/FASTA MetaGenome",
                    },
                ],
                {
                    "prefix": "oscar_the_grouch_does_meth",
                    "suffix": "FaStA.gz",
                    "file_ext_type": ["FASTA"],
                },
            ),
        ),
        (
            "look.at.all.these.frigging.dots.gff2.gzip",
            (
                [
                    {
                        "app_weight": 1,
                        "id": "gff_genome",
                        "title": "GFF/FASTA Genome",
                    },
                    {
                        "app_weight": 1,
                        "id": "gff_metagenome",
                        "title": "GFF/FASTA MetaGenome",
                    },
                ],
                {
                    "prefix": "look.at.all.these.frigging.dots",
                    "suffix": "gff2.gzip",
                    "file_ext_type": ["GFF"],
                },
            ),
        ),
    ]

    for filename, importers in test_data:
        assert (
            AutoDetectUtils.determine_possible_importers(filename) == importers
        ), filename


def test_sra_mappings():
    """
    Just testing a single app
    :return:
    """
    sra_file = "test.sra"
    possible_importers, fileinfo = AutoDetectUtils.determine_possible_importers(
        filename=sra_file
    )
    assert possible_importers == [
        {
            "id": "sra_reads",
            "app_weight": 1,
            "title": "SRA Reads",
        }
    ]
    assert fileinfo == {"prefix": "test", "suffix": "sra", "file_ext_type": ["SRA"]}


def test_zip_mappings():
    """
    Just testing a single app
    :return:
    """
    gz_file = "test.tar.gz"
    possible_importers, fileinfo = AutoDetectUtils.determine_possible_importers(
        filename=gz_file
    )
    assert possible_importers == [
        {
            "id": "decompress",
            "app_weight": 1,
            "title": "Decompress/Unpack",
        }
    ]
    assert fileinfo == {
        "prefix": "test",
        "suffix": "tar.gz",
        "file_ext_type": ["CompressedFileFormatArchive"],
    }


def test_get_mappings():
    """
    Basic test of the get mappings logic. Most of the logic is in determine_possible_importers
    which is thoroughly tested above.
    """
    assert AutoDetectUtils.get_mappings(
        ["filename", "file.name.Gz", "some.dots.gff3.gz"]
    ) == {
        "mappings": [
            None,
            [
                {
                    "app_weight": 1,
                    "id": "decompress",
                    "title": "Decompress/Unpack",
                }
            ],
            [
                {
                    "app_weight": 1,
                    "id": "gff_genome",
                    "title": "GFF/FASTA Genome",
                },
                {
                    "app_weight": 1,
                    "id": "gff_metagenome",
                    "title": "GFF/FASTA MetaGenome",
                },
            ],
        ],
        "fileinfo": [
            {"prefix": "filename", "suffix": None, "file_ext_type": []},
            {
                "prefix": "file.name",
                "suffix": "Gz",
                "file_ext_type": ["CompressedFileFormatArchive"],
            },
            {"prefix": "some.dots", "suffix": "gff3.gz", "file_ext_type": ["GFF"]},
        ],
    }
