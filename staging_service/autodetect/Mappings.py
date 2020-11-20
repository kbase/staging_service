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
PHENOTYPE = "PHENOTYPE"  # "KBasePhenotypes.PhenotypeSet"
ESCHER = "ESCHER"
ANNOTATIONS = "ANNOTATIONS"

# Omitting file.sanfastq
# GFF3 = "GFF3" do we need to only allow GFF3 and not support GFF2/GFF1?

MEDIA = "KBaseBiochem.Media"

# These ID mappings should be available in dropdown_order in staging_upload.json in the narrative service
fastq_reads_id = "fastq_reads"
sra_reads_id = "sra_reads"
genbank_genome_id = "genbank_genome"
gff_genome_id = "gff_genome"
gff_metagenome_id = "gff_metagenome"
expression_matrix_id = "expression_matrix"
media_id = "media"
fba_model_id = "fba_model"
assembly_id = "assembly"
phenotype_set_id = "phenotype_set"
sample_set_id = "sample_set"

# To be added to https://github.com/kbase/narrative/kbase-extension/static/kbase/config/staging_upload.json
decompress_id = "decompress"
metabolic_annotations_id = "metabolic_annotation"
metabolic_annotations_bulk_id = "metabolic_annotation_bulk"
attribute_mapping_id = "attribute_mapping"
escher_map_id = "escher_map"

type_to_extension_mapping = {
    FASTA: ["fna", "fa", "faa", "fsa", "fasta"],
    FASTQ: ["fq", "fastq"],
    GFF: ["gff", "gff2", "gff3"],
    # GTF: ["gtf"],
    SRA: ["sra"],
    GENBANK: ["gbk", "genbank"],
    # SAM: ["sam"],
    # VCF: ["vcf"],
    # MSA: [
    #     "clustal",
    #     "clustalw",
    #     "emboss",
    #     "embl",
    #     "ig",
    #     "maf",
    #     "maue",
    #     "fna",
    #     "fa",
    #     "faa",
    #     "fsa",
    #     "phylip",
    #     "stockholm",
    # ],
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
