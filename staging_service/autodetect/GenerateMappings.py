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
        "id": sra_reads_id,
        "title": "SRA Reads",
        "app": "kb_uploadmethods/import_sra_as_reads_from_staging",
        "output_type": ["KBaseFile.SingleEndLibrary", "KBaseFile.PairedEndLibrary"],
    }
]

mapping[FASTQ] = [
    {
        "id": fastq_reads_interleaved_id,
        "title": "FastQ Reads Interleaved",
        "app": "kb_uploadmethods/import_fastq_interleaved_as_reads_from_staging",
        "output_type": ["KBaseFile.SingleEndLibrary", "KBaseFile.PairedEndLibrary"],
    },
    {
        "id": fastq_reads_noninterleaved_id,
        "title": "FastQ Reads NonInterleaved",
        "app": "kb_uploadmethods/import_fastq_noninterleaved_as_reads_from_staging",
        "output_type": ["KBaseFile.SingleEndLibrary", "KBaseFile.PairedEndLibrary"],
    },
]

mapping[FASTA] = [
    {
        "id": assembly_id,
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
        "id": gff_genome_id,
        "title": "GFF/FASTA Genome",
        "app": "kb_uploadmethods/import_gff_fasta_as_genome_from_staging",
        "output_type": ["KBaseGenomes.Genome"],
    },
    {
        "id": gff_metagenome_id,
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
        "id": genbank_genome_id,
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
        "id": gff_genome_id,
        "title": "GFF/FASTA Genome",
        "app": "kb_uploadmethods/import_gff_fasta_as_genome_from_staging",
        "output_type": ["KBaseGenomes.Genome"],
    },
    {
        "id": gff_metagenome_id,
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
        "id": decompress_id,
        "title": "Decompress/Unpack",
        "app": "kb_uploadmethods/unpack_staging_file",
        "output_type": [None],
    }
]
mapping[CSV] = [
    {
        "id": sample_set_id,
        "title": "Samples",
        "app": "sample_uploader/import_samples",
        "output_type": ["KBaseSets.SampleSet"],
    }
]

mapping[TSV] = [
    {
        "id": media_id,
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
        "id": expression_matrix_id,
        "title": "Expression Matrix",
        "app": "kb_uploadmethods/import_tsv_as_expression_matrix_from_staging",
        "output_type": ["KBaseFeatureValues.ExpressionMatrix"],
    },
    {
        "id": metabolic_annotations_id,
        "title": "Metabolic Annotations",
        "app": "MergeMetabolicAnnotations/import_annotations",
        "output_type": ["KBaseGenomes.Genome"],
    },
    {
        "id": metabolic_annotations_bulk_id,
        "title": "Bulk Metabolic Annotations",
        "app": "MergeMetabolicAnnotations/import_bulk_annotations",
        "output_type": ["KBaseGenomes.Genome"],
    },
    {
        "id": fba_model_id,
        "title": "FBA Model",
        "app": "kb_uploadmethods/import_file_as_fba_model_from_staging",
        "output_type": ["KBaseFBA.FBAModel"],
    },
    {
        "id": phenotype_set_id,
        "title": "Phenotype Set",
        "app": "kb_uploadmethods/import_tsv_as_phenotype_set_from_staging",
        "output_type": ["KBasePhenotypes.PhenotypeSet"],
    },
]

mapping[EXCEL] = [
    {
        "id": sample_set_id,
        "title": "Samples",
        "app": "sample_uploader/import_samples",
        "output_type": ["KBaseSets.SampleSet"],
    },
    {
        "id": media_id,
        "title": "Media",
        "app": "kb_uploadmethods/import_tsv_excel_as_media_from_staging",
        "output_type": ["KBaseBiochem.Media"],
    },
    {
        "id": attribute_mapping_id,
        "title": "Attribute Mapping",
        "app": "kb_uploadmethods/import_attribute_mapping_from_staging",
        "output_type": ["KBaseExperiments.AttributeMapping"],
    },
    {
        "id": fba_model_id,
        "title": "FBA Model",
        "app": "kb_uploadmethods/import_file_as_fba_model_from_staging",
        "output_type": ["KBaseFBA.FBAModel"],
    },
]
mapping[JSON] = [
    {
        "id": escher_map_id,
        "title": "EscherMap",
        "app": "kb_uploadmethods/import_eschermap_from_staging",
        "output_type": ["KBaseFBA.EscherMap"],
    }
]

mapping[SBML] = [
    {
        "id": fba_model_id,
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
counter = 0
for category in mapping:
    apps = mapping[category]
    for app in apps:
        # print("looking at", app)
        title = app["title"]

        if title not in new_apps:
            # Create a new entry for extensions and id in the app
            app["extensions"] = []
            app["_id"] = counter
            counter += 1
            new_apps[title] = copy.copy(app)
        # Then for the current app we are looking at,
        # add appropriate file extensions
        new_apps[title]["extensions"].extend(
            type_to_extension_mapping[category]
        )

# Then create the mapping between file extensions and apps
# For example, the .gbk and .genkbank extensions map to app with id of 6
# so the mapping would look like
# mapping['gbk'] =
"""
    "gbk": [
      {
        "id": "genbank_genome",
        "title": "genbank_genome",
        "app_weight": 1
      }
    ],
"""

# with "genbank_genome" being the id of the matched app
# and 1 being a perfect weight score of 100%
extensions_mapping = defaultdict(list)
for app_title in new_apps:

    app = new_apps[app_title]
    app_id = app["id"]
    extensions = app["extensions"]

    perfect_match_weight = 1
    for extension in extensions:
        extensions_mapping[extension].append(
            {"id": app_id, "title": app_title, "app_weight": perfect_match_weight}
        )

if __name__ == "__main__":
    import json

    print("About to generate supported apps with extensions")
    data = {"apps": new_apps, "types": extensions_mapping}
    with open("supported_apps_w_extensions.json", "w") as f:
        json.dump(obj=data, fp=f, indent=2)
