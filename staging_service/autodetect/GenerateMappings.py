"""
* This script generates various potential api responses and serves as a list of supported apps and extensions
for the staging service endpoint .
* Afterwards, we can pick a json file and edit those, or keep editing this file in the future to generate the mappings


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
* Note: This doesn't handle if we want to have different output types based on file extensions feeding into the same app
"""
from collections import defaultdict

from staging_service.autodetect.Mappings import *

# Note that some upload apps are not included - in particular batch apps, which are now
# redundant, and MSAs and attribute mappings because they're out of scope at the current time.

app_id_to_title = {
    sra_reads_id: "SRA Reads",
    fastq_reads_interleaved_id: "FastQ Reads Interleaved",
    fastq_reads_noninterleaved_id: "FastQ Reads NonInterleaved",
    assembly_id: "Assembly",
    gff_genome_id: "GFF/FASTA Genome",
    gff_metagenome_id: "GFF/FASTA MetaGenome",
    genbank_genome_id: "Genbank Genome",
    decompress_id: "Decompress/Unpack",
    sample_set_id: "Samples",
    media_id: "Media",
    expression_matrix_id: "Expression Matrix",
    metabolic_annotations_id: "Metabolic Annotations",
    metabolic_annotations_bulk_id: "Bulk Metabolic Annotations",
    fba_model_id: "FBA Model",
    phenotype_set_id: "Phenotype Set",
    escher_map_id: "EscherMap",
}


file_format_to_app_mapping = {}

file_format_to_app_mapping[SRA] = [sra_reads_id]
file_format_to_app_mapping[FASTQ] = [fastq_reads_interleaved_id, fastq_reads_noninterleaved_id]
file_format_to_app_mapping[FASTA] = [assembly_id, gff_genome_id, gff_metagenome_id]
file_format_to_app_mapping[GENBANK] = [genbank_genome_id]
file_format_to_app_mapping[GFF] = [gff_genome_id, gff_metagenome_id]
file_format_to_app_mapping[ZIP] = [decompress_id]
file_format_to_app_mapping[CSV] = [sample_set_id]
file_format_to_app_mapping[TSV] = [media_id, expression_matrix_id, metabolic_annotations_id,
                metabolic_annotations_bulk_id, fba_model_id, phenotype_set_id]
file_format_to_app_mapping[EXCEL] = [sample_set_id, media_id, fba_model_id]
file_format_to_app_mapping[JSON] = [escher_map_id]
file_format_to_app_mapping[SBML] = [fba_model_id]

app_id_to_extensions = defaultdict(list)
for filecat, apps in file_format_to_app_mapping.items():
    for app_id in apps:
        app_id_to_extensions[app_id].extend(file_format_to_extension_mapping[filecat])

# Create the mapping between file extensions and apps
# For example, the .gbk and .genkbank extensions map to app with id of "genbank_genome"
# so the mapping would look like
# mapping['gbk'] =
"""
    "gbk": [
      {
        "id": "genbank_genome",
        "app_weight": 1
      }
    ],
"""

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
                # detection. For backwards compatibilily, we'd leave the current FASTQ type and
                # add a FASTQ-FWD or FWD type or something.
                "file_ext_type": [extension_to_file_format_mapping[extension]],
                "mappings": []
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
        "types": extensions_mapping}
    with open("supported_apps_w_extensions.json", "w") as f:
        json.dump(obj=data, fp=f, indent=2)
