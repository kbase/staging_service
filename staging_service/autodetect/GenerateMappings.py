"""
* This script generates various potential api responses and serves as a list of supported apps and extensions
for the staging service endpoint .
* Afterwards, we can pick a json file and edit those, or keep editing this file in the future to generate the mappings


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

* Note: We should serve the generated content from memory
* Note: This doesn't handle if we want to have different output types based on file extensions feeding into the same app
"""
import copy
from collections import defaultdict, OrderedDict

from staging_service.autodetect.Mappings import *

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
    # Commented out because: Batch App
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
    # Commented out because: Batch App
    # {
    #     "title": "GFF/FASTA Genome Set",
    #     "app": "kb_uploadmethods/batch_import_genome_from_staging",
    #     "output_type": ["KBaseSearch.GenomeSet"],
    #     "comment" : "To use: select a directory from the narrative"
    # },
    # Commented out because: It doesn't conform to standards and is out of scope right now
    # {
    #     "title": "Multiple Sequence Alignment",
    #     "app": "MSAUtils/import_msa_file",
    #     "output_type": ["KBaseTrees.MSA"],
    # },
]
# Commented out because: It doesn't conform to standards and is out of scope right now
# mapping[MSA] = [
# {
#     "title": "Multiple Sequence Alignment",
#     "app": "MSAUtils/import_msa_file",
#     "output_type": ["KBaseTrees.MSA"],
# }
# ]

mapping[GENBANK] = [
    {
        "title": "Genbank Genome",
        "app": "kb_uploadmethods/import_genbank_as_genome_from_staging",
        "output_type": ["KBaseGenomes.Genome"],
    },
    # Commented out because: Batch App
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
    # Commented out because: Batch App
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
    # Commented out because: Not in scope and requires an object
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

"""
This turns an app from this

      "title": "Genbank Genome",
      "app": "kb_uploadmethods/import_genbank_as_genome_from_staging",
      "output_type": [
        "KBaseGenomes.Genome"
      ],

to


 "Genbank Genome": {
      "title": "Genbank Genome",
      "app": "kb_uploadmethods/import_genbank_as_genome_from_staging",
      "output_type": [
        "KBaseGenomes.Genome"
      ],
      "extensions": [
        "gbk",
        "genbank"
      ],
      "id": 6
    },

"""

"""
For each category in mapping (current SMBl/JSOn/FASTQ/FASTA/ etc), get an "App"
Create the app in a list of  using the title as the primary hashing key
Add a list of extensions, such as .fa, fasta
Add a unique id, such as 1,2,3
"""

new_apps = OrderedDict()
extensions_flat = []
counter = 0
for category in mapping:
    apps = mapping[category]
    for app in apps:
        # print("looking at", app)
        title = app["title"].replace(" ", "_").lower()

        if title not in new_apps:
            # Create a new entry for extensions and id in the app
            app["extensions"] = []
            app["id"] = counter
            counter += 1
            new_apps[title] = copy.copy(app)
        # Then for the current app we are looking at,
        # find the appropriate category and append its extensions list
        # to the apps list of extensions
        for extension in type_to_extension_mapping:
            if extension == category:
                new_apps[title]["extensions"].extend(
                    type_to_extension_mapping[extension]
                )
                extensions_flat.extend(type_to_extension_mapping[extension])

# Then create the mapping between file extensions and apps
# For example, the .gbk and .genkbank extensions map to app with id of 6
# so the mapping would look like
# mapping['gbk'] =
"""
    "gbk": [
      {
        "id": 6,
        "title": "genbank_genome",
        "app_weight": 1
      }
    ],
"""

# with 6 being the id of the matched app
# and 1 being a perfect weight score of 100%
extensions_mapping = defaultdict(list)
for app_title in new_apps:

    app = new_apps[app_title]
    app_id = app["id"]
    extensions = app["extensions"]

    perfect_match_weight = 1
    for extension in extensions:
        extensions_mapping[extension].append(
            {'id': app_id, 'title': app_title, 'app_weight': perfect_match_weight})

if __name__ == "__main__":
    import json

    print("About to generate supported apps with extensions")
    data = {"apps": new_apps, "types": extensions_mapping}
    with open("supported_apps_w_extensions.json", "w") as f:
        json.dump(obj=data, fp=f, indent=2)
