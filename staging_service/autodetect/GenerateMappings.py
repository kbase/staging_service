"""
* This script generates various potential api responses and serves as a list of supported apps 
  and extensions for the staging service endpoint .
* Afterwards, we can pick a json file and edit those, or keep editing this file in the future 
  to generate the mappings


================================
# In Scope Importer Apps
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
* Note: This doesn't handle if we want to have different output types based on file extensions
  feeding into the same app
"""
from collections import defaultdict

from staging_service.autodetect import Mappings

# Note that some upload apps are not included - in particular batch apps, which are now
# redundant, and MSAs and attribute mappings because they're out of scope at the current time.

app_id_to_title = {
    Mappings.sra_reads_id: "SRA Reads",
    Mappings.fastq_reads_interleaved_id: "FastQ Reads Interleaved",
    Mappings.fastq_reads_noninterleaved_id: "FastQ Reads NonInterleaved",
    Mappings.assembly_id: "Assembly",
    Mappings.gff_genome_id: "GFF/FASTA Genome",
    Mappings.gff_metagenome_id: "GFF/FASTA MetaGenome",
    Mappings.genbank_genome_id: "Genbank Genome",
    Mappings.decompress_id: "Decompress/Unpack",
    Mappings.sample_set_id: "Samples",
    Mappings.media_id: "Media",
    Mappings.expression_matrix_id: "Expression Matrix",
    Mappings.metabolic_annotations_id: "Metabolic Annotations",
    Mappings.metabolic_annotations_bulk_id: "Bulk Metabolic Annotations",
    Mappings.fba_model_id: "FBA Model",
    Mappings.phenotype_set_id: "Phenotype Set",
    Mappings.escher_map_id: "EscherMap",
    Mappings.import_specification: "Import Specification",
}


file_format_to_app_mapping = {}

file_format_to_app_mapping[Mappings.SRA] = [Mappings.sra_reads_id]
file_format_to_app_mapping[Mappings.FASTQ] = [
    Mappings.fastq_reads_interleaved_id,
    Mappings.fastq_reads_noninterleaved_id,
]
file_format_to_app_mapping[Mappings.FASTA] = [
    Mappings.assembly_id,
    Mappings.gff_genome_id,
    Mappings.gff_metagenome_id,
]
file_format_to_app_mapping[Mappings.GENBANK] = [Mappings.genbank_genome_id]
file_format_to_app_mapping[Mappings.GFF] = [
    Mappings.gff_genome_id,
    Mappings.gff_metagenome_id,
]
file_format_to_app_mapping[Mappings.ZIP] = [Mappings.decompress_id]
file_format_to_app_mapping[Mappings.CSV] = [
    Mappings.sample_set_id,
    Mappings.import_specification,
]
file_format_to_app_mapping[Mappings.TSV] = [
    Mappings.media_id,
    Mappings.expression_matrix_id,
    Mappings.metabolic_annotations_id,
    Mappings.metabolic_annotations_bulk_id,
    Mappings.fba_model_id,
    Mappings.phenotype_set_id,
    Mappings.import_specification,
]
file_format_to_app_mapping[Mappings.EXCEL] = [
    Mappings.sample_set_id,
    Mappings.media_id,
    Mappings.fba_model_id,
    Mappings.import_specification,
]
file_format_to_app_mapping[Mappings.JSON] = [Mappings.escher_map_id]
file_format_to_app_mapping[Mappings.SBML] = [Mappings.fba_model_id]

app_id_to_extensions = defaultdict(list)
for filecat, apps in file_format_to_app_mapping.items():
    for app_id in apps:
        app_id_to_extensions[app_id].extend(
            Mappings.file_format_to_extension_mapping[filecat]
        )

# Create the mapping between file extensions and apps
# For example, the .gbk and .genkbank extensions map to app with id of "genbank_genome"
# so the mapping would look like
# mapping['gbk'] =
# """
#     "gbk": [
#       {
#         "id": "genbank_genome",
#         "app_weight": 1
#       }
#     ],
# """

# with "genbank_genome" being the id of the matched app
# and 1 being a perfect weight score of 100%
extensions_mapping = {}
for app_id in app_id_to_extensions:
    perfect_match_weight = 1
    for extension in app_id_to_extensions[app_id]:
        if extension not in extensions_mapping:
            extensions_mapping[extension] = {
                # make a list to allow for expansion in the future - for example it could
                # include whether reads are forward or reverse if we get smarter about name
                # detection. For backwards compatability, we'd leave the current FASTQ type and
                # add a FASTQ-FWD or FWD type or something.
                "file_ext_type": [Mappings.extension_to_file_format_mapping[extension]],
                "mappings": [],
            }
        extensions_mapping[extension]["mappings"].append(
            {
                "id": app_id,
                "title": app_id_to_title[app_id],
                "app_weight": perfect_match_weight,
            }
        )

if __name__ == "__main__":
    import json

    print("About to generate supported apps with extensions")
    data = {
        # this is currently unused by the code base, but we include it to make it easy to
        # see what file extensions are registered for each app
        "app_to_ext": app_id_to_extensions,
        "types": extensions_mapping,
    }
    with open("supported_apps_w_extensions.json", "w", encoding="utf-8") as f:
        json.dump(obj=data, fp=f, indent=2)
