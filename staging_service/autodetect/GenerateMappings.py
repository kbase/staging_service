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
import copy
import json
from collections import defaultdict
from pprint import pprint

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

# apps_list = {}
apps_list_unique = {}
list_of_apps = []
extensions_flat = []
counter = 0

for datatype in type_to_extension_mapping:
    for file_extension in type_to_extension_mapping[datatype]:
        extensions_flat.append(file_extension)
        extension_to_type_mapping[file_extension.lower()].append(datatype)
        available_apps = mapping[datatype]
        # Give each entry a counter
        for app in available_apps:
            app_copy = copy.copy(app)
            title = app_copy["title"]
            app_copy["id"] = counter
            app_copy["extensions"] = type_to_extension_mapping[datatype]
            list_of_apps.append(app_copy)
            counter += 1
        pprint(["apps list now contains ", len(list_of_apps), list_of_apps])

extensions_flat = list(set(extensions_flat))
type_to_app_mapping_with_weights = defaultdict(list)
for extension in extensions_flat:
    print("Working on", extensions_flat)
    for app in list_of_apps:
        extension_list = app["extensions"]
        if extension in extension_list:
            mapping_tuple = [app["id"], 1]
            if mapping_tuple not in type_to_app_mapping_with_weights[extension]:
                type_to_app_mapping_with_weights[extension].append(mapping_tuple)

if __name__ == "__main__":
    pprint(type_to_app_mapping_with_weights)
    data = {"apps": list_of_apps, "types": type_to_app_mapping_with_weights}
    with open("./autodetect/supported_apps_w_extensions.json", "w") as f:
        json.dump(obj=data, fp=f, indent=2)
