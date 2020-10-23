"""
* This script generates various potential api responses and serves as a list of supported apps and extensions
for the staging service endpoint .
* Afterwards, we can pick a json or yaml file and edit those, or keep editing this file in the future to generate the mappings


================================
# In Scope Importer Apps
* Note: FastQ Interleaved/Uninterleaved custom UIs not yet implemented
* Note: MergeMetabolicAnnotations and PredictPhenotypes also require an object in addition to a file

================================
# Out of scope importer notes
* Note: MultipleSequenceAlignmentApp Commented out because it has a weird interface

================================
# Batch App Importer notes
* Commented out all batch apps, as those take a directory from the narrative itself

Functionality: Running this script will
* Save this indirectly as a json file
* Save this indirectly as a yaml file

* Note: We should serve the generated content from memory
"""
import json
from collections import defaultdict

# Requires pyyaml
import yaml
from pprint import pprint

# Regular Formats
JSON = "JSON"
TSV = "TSV"
CSV = "CSV"
EXCEL = "EXCEL"
ZIP = "CompressedFileFormatArchive"

# BIOINFORMATICS FORMATS
FASTA = "FASTA"
FASTQ = "FASTQ Reads"
GFF = "GFF"
GTF = "GTF"
SRA = "SRA"
SAM = "SAM"
BAM = "BAM"
GENBANK = "GENBANK"
VCF = "VCF"
FBA = "FBAModel"
SBML = "SBML"

# KBASE SPECIFIC FORMATS
MSA = "MultipleSequenceAlignment"
PHENOTYPE = "PHENOTYPE"
ESCHER = "ESCHER"
ANNOTATIONS = "ANNOTATIONS"

# Omitting file.sanfastq
# GFF3 = "GFF3" do we need to only allow GFF3 and not support GFF2/GFF1?

MEDIA = "KBaseBiochem.Media"
PHENOTYPE = "KBasePhenotypes.PhenotypeSet"

type_to_extension_mapping = {
    FASTA: ["fna", "fa", "faa", "fsa", "fasta"],
    FASTQ: ["fq", "fastq"],
    GFF: ["gff", "gff2", "gff3"],
    GTF: ["gtf"],
    SRA: ["sra"],
    GENBANK: ["gbk"],
    SAM: ["sam"],
    VCF: ["vcf"],
    MSA: [
        "clustal",
        "clustalw",
        "emboss",
        "embl",
        "ig",
        "maf",
        "maue",
        "fna",
        "fa",
        "faa",
        "fsa",
        "phylip",
        "stockholm",
    ],
    TSV: ["tsv"],
    CSV: ["csv"],
    JSON: ["json"],
    EXCEL: ["xls", "xlsx"],
    ZIP: ["zip", "tar", "tgz", "tar.gz", "7z", "gz", "gzip", "rar"],
    SBML: ["smbl"],
    # Custom File Types?
    MEDIA: ["tsv", "xls", "xlsx"],
    PHENOTYPE: ["tsv"],
    ESCHER: ["json"],
    ANNOTATIONS: ["tsv"],
    FBA: ["tsv", "xls", "xlsx", "smbl"],
}

mapping = defaultdict(list)

mapping[SRA] = [
    {
        "title": "SRA Reads",
        "app": "kb_uploadmethods/import_fastq_sra_as_reads_from_staging",
        "output_type": ["KBaseFile.SingleEndLibrary", "KBaseFile.PairedEndLibrary"],
    }
]

mapping[FASTQ] = [
    {
        "title": "FastQ Reads Interleaved",
        "app": "kb_uploadmethods/import_fastq_sra_as_reads_from_staging",
        "output_type": ["KBaseFile.SingleEndLibrary", "KBaseFile.PairedEndLibrary"],
    },
    {
        "title": "FastQ Reads UnInterleaved",
        "app": "kb_uploadmethods/import_fastq_sra_as_reads_from_staging",
        "output_type": ["KBaseFile.SingleEndLibrary", "KBaseFile.PairedEndLibrary"],
    },
]

mapping[FASTA] = [
    {
        "title": "Assembly",
        "app": "kb_uploadmethods/import_fasta_as_assembly_from_staging",
        "output_type": ["KBaseGenomeAnnotations.Assembly"],
    },
    # {
    #     "title": "Assembly Set",
    #     "app": "kb_uploadmethods/batch_import_assembly_from_staging",
    #     "output_type": ["KBaseSets.AssemblySet"],
    # },
    {
        "title": "GFF/FASTA Genome",
        "app": "kb_uploadmethods/import_gff_fasta_as_genome_from_staging",
        "output_type": ["KBaseGenomes.Genome"],
    },
    {
        "title": "GFF/FASTA MetaGenome",
        "app": "kb_uploadmethods/import_gff_fasta_as_metagenome_from_staging",
        "output_type": ["KBaseMetagenomes.AnnotatedMetagenomeAssembly"],
    },
    # {
    #     "title": "GFF/FASTA Genome Set",
    #     "app": "kb_uploadmethods/batch_import_genome_from_staging",
    #     "output_type": ["KBaseSearch.GenomeSet"],
    #     "comment" : "To use: select a directory from the narrative"
    # },
    # {
    #     "title": "Multiple Sequence Alignment",
    #     "app": "MSAUtils/import_msa_file",
    #     "output_type": ["KBaseTrees.MSA"],
    # },
]
mapping[MSA] = [
    # {
    #     "title": "Multiple Sequence Alignment",
    #     "app": "MSAUtils/import_msa_file",
    #     "output_type": ["KBaseTrees.MSA"],
    # }
]

mapping[GENBANK] = [
    {
        "title": "Genbank Genome",
        "app": "kb_uploadmethods/import_genbank_as_genome_from_staging",
        "output_type": ["KBaseGenomes.Genome"],
    },
    # {
    #     "title": "Genbank Genome Set",
    #     "app": "kb_uploadmethods/batch_import_genome_from_staging",
    #     "output_type": ["KBaseSearch.GenomeSet"],
    #     "hidden" : True
    # },
]

mapping[GFF] = [
    {
        "title": "GFF/FASTA Genome",
        "app": "kb_uploadmethods/import_gff_fasta_as_genome_from_staging",
        "output_type": ["KBaseGenomes.Genome"],
    },
    {
        "title": "GFF/FASTA MetaGenome",
        "app": "kb_uploadmethods/import_gff_fasta_as_metagenome_from_staging",
        "output_type": ["KBaseMetagenomes.AnnotatedMetagenomeAssembly"],
    },
    # {
    #     "title": "GFF/FASTA Genome Set",
    #     "app": "kb_uploadmethods/batch_import_genome_from_staging",
    #     "output_type": ["KBaseSearch.GenomeSet"],
    #     "hidden": True
    # },
]

mapping[ZIP] = [
    {
        "title": "Decompress/Unpack",
        "app": "kb_uploadmethods/unpack_staging_file",
        "output_type": [None],
    }
]
mapping[CSV] = [
    {
        "title": "Samples",
        "app": "sample_uploader/import_samples",
        "output_type": ["KBaseSets.SampleSet"],
    }
]

mapping[TSV] = [
    {
        "title": "Media",
        "app": "kb_uploadmethods/import_tsv_excel_as_media_from_staging",
        "output_type": ["KBaseBiochem.Media"],
    },
    # {
    #     "title": "Attribute Mapping",
    #     "app": "kb_uploadmethods/import_attribute_mapping_from_staging",
    #     "output_type": ["KBaseExperiments.AttributeMapping"],
    # },
    {
        "title": "Expression Matrix",
        "app": "kb_uploadmethods/import_tsv_as_expression_matrix_from_staging",
        "output_type": ["KBaseFeatureValues.ExpressionMatrix"],
    },
    {
        "title": "Metabolic Annotations",
        "app": "MergeMetabolicAnnotations/import_annotations",
        "output_type": ["KBaseGenomes.Genome"],
    },
    {
        "title": "Bulk Metabolic Annotations",
        "app": "MergeMetabolicAnnotations/import_bulk_annotations",
        "output_type": ["KBaseGenomes.Genome"],
    },
    {
        "title": "FBA Model",
        "app": "kb_uploadmethods/import_file_as_fba_model_from_staging",
        "output_type": ["KBaseFBA.FBAModel"],
    },
    {
        "title": "Phenotype Set",
        "app": "kb_uploadmethods/import_tsv_as_phenotype_set_from_staging",
        "output_type": ["KBasePhenotypes.PhenotypeSet"],
    },
]

mapping[EXCEL] = [
    {
        "title": "Samples",
        "app": "sample_uploader/import_samples",
        "output_type": ["KBaseSets.SampleSet"],
    },
    {
        "title": "Media",
        "app": "kb_uploadmethods/import_tsv_excel_as_media_from_staging",
        "output_type": ["KBaseBiochem.Media"],
    },
    {
        "title": "Attribute Mapping",
        "app": "kb_uploadmethods/import_attribute_mapping_from_staging",
        "output_type": ["KBaseExperiments.AttributeMapping"],
    },
    {
        "title": "FBA Model",
        "app": "kb_uploadmethods/import_file_as_fba_model_from_staging",
        "output_type": ["KBaseFBA.FBAModel"],
    },
]
mapping[JSON] = [
    {
        "title": "EscherMap",
        "app": "kb_uploadmethods/import_eschermap_from_staging",
        "output_type": ["KBaseFBA.EscherMap"],
    }
]

mapping[SBML] = [
    {
        "title": "FBA Model",
        "app": "kb_uploadmethods/import_file_as_fba_model_from_staging",
        "output_type": ["KBaseFBA.FBAModel"],
    }
]

extension_to_type_mapping = defaultdict(list)


apps_list = {}
apps_list_unique = {}
apps_list_list = []
extensions_flat = []
counter = 0
for datatype in type_to_extension_mapping:
    for file_extension in type_to_extension_mapping[datatype]:
        extensions_flat.append(file_extension)
        extension_to_type_mapping[file_extension.lower()].append(datatype)
        available_apps = mapping[datatype]
        # Give each entry a counter
        for app in available_apps:
            title = app["title"]
            if title in apps_list:
                continue
            apps_list[title] = app
            app["id"] = counter
            app["extensions"] = type_to_extension_mapping[datatype]
            apps_list_unique[counter] = app
            apps_list_list.append(app)
            counter += 1

extensions_flat = list(set(extensions_flat))
type_to_app_mapping_with_weights = defaultdict(list)
for extension in extensions_flat:
    for app in apps_list_list:
        extension_list = app["extensions"]
        if extension in extension_list:
            app_id = app["id"]
            type_to_app_mapping_with_weights[extension].append([app_id, 1])


pprint(type_to_app_mapping_with_weights)


# So uniqueify them above
# Give them an index
# Save them with an id field inside
# Build mapping based off of the title, and the id inside

# Maybe start over and build apps in a seperate file with IDs
# Then associate the mappings with IDs instead
# Then iterate over file extensions, collecting the ids/weigths of possible importers


# for datatype in type_to_extension_mapping:
#     for file_extension in type_to_extension_mapping[datatype]:
#


# yaml.Dumper.ignore_aliases = lambda *args: True

# print("Extension to type mapping")
# dumps = json.dumps(extension_to_type_mapping, indent=2)
# print(dumps)
#
# with open("./autodetect/extension_to_type.json", "w") as f:
#     json.dump(obj=extension_to_type_mapping, fp=f, indent=2)
#
# with open("./autodetect/extension_to_type.yaml", "w") as f:
#     yaml.dump(dict(extension_to_type_mapping), f)
#
# print("Extension to app mapping")
# dumps = json.dumps(extension_to_app_mapping, indent=2)
# print(dumps)
#
# with open("./autodetect/extension_to_app.json", "w") as f:
#     json.dump(obj=extension_to_app_mapping, fp=f, indent=2)
#
# with open("./autodetect/extension_to_app.yaml", "w") as f:
#     yaml.dump(dict(extension_to_app_mapping), f)
#
# print("Supported Apps List")
# dumps = json.dumps(apps_list_unique, indent=2)
# print(dumps)
#
# with open("./autodetect/supported_apps.json", "w") as f:
#     json.dump(obj=apps_list_unique, fp=f, indent=2)
#
# with open("./autodetect/supported_apps.yaml", "w") as f:
#     yaml.dump(dict(apps_list_unique), f)
#

# print("Supported Apps List2")
# dumps = json.dumps(apps_list_list, indent=2)
# print(dumps)

data = {"apps": apps_list_list, "types": type_to_app_mapping_with_weights}

with open("./autodetect/supported_apps_w_extensions.json", "w") as f:
    json.dump(obj=data, fp=f, indent=2)

# with open("./autodetect/supported_apps_w_extensions.yaml", "w") as f:
#     yaml.dump(dict(apps_list_list), f)
#
#
