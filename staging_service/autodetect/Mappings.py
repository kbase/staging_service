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
