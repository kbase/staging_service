"""
* Save this indirectly as a json file
* Save this indirectly as a yaml file
* Serve that generated content from memory

"""
from collections import defaultdict

TSV = "TSV"
FASTA = "FASTA"
FASTQ = "FASTQ Reads"
GFF = "GFF"
CSV = "CSV"
EXCEL = "EXCEL"
GTF = "GTF"
SRA = "SRA"
SAM = "SAM"
BAM = "BAM"
GENBANK = "GENBANK"
VCF = "VCF"
MSA = "MultipleSequenceAlignment"
ZIP = "CompressedFileFormatArchive"
FBA = "FBAModel"
PHENOTYPE = "PHENOTYPE"
ESCHER = "ESCHER"
ANNOTATIONS = "ANNOTATIONS"

# Omitting file.sanfastq
# GFF3 = "GFF3" do we need to only allow GFF3 and not support GFF2/GFF1?

MEDIA = "KBaseBiochem.Media"
PHENOTYPE = "KBasePhenotypes.PhenotypeSet"

type_to_extension_mapping = {
    FASTA: ["fna", "fa", "faa", "fsa"],
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
    ZIP: ["zip", "tar", "tgz", "tar.gz", "7z", "gz", "gzip", "rar"],
    MEDIA: ["tsv", "xls", "xlsx"],
    PHENOTYPE: ["tsv"],
    ESCHER: ["json"],
    ANNOTATIONS: ["tsv"],
    FBA: [],
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
    {
        "title": "Assembly Set",
        "app": "kb_uploadmethods/batch_import_assembly_from_staging",
        "output_type": ["KBaseSets.AssemblySet"],
    },
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
    {
        "title": "GFF/FASTA Genome Set",
        "app": "kb_uploadmethods/batch_import_genome_from_staging",
        "output_type": ["KBaseSearch.GenomeSet"],
    },
    {
        "title": "Multiple Sequence Alignment",
        "app": "MSAUtils/import_msa_file",
        "output_type": ["KBaseTrees.MSA"],
    },
]
mapping[MSA] = [
    {
        "title": "Multiple Sequence Alignment",
        "app": "MSAUtils/import_msa_file",
        "output_type": ["KBaseTrees.MSA"],
    }
]

mapping[GENBANK] = [
    {
        "title": "Genbank Genome ",
        "app": "kb_uploadmethods/import_genbank_as_genome_from_staging",
        "output_type": ["KBaseGenomes.Genome"],
    },
    {
        "title": "Genbank Genome Set",
        "app": "kb_uploadmethods/batch_import_genome_from_staging",
        "output_type": ["KBaseSearch.GenomeSet"],
    },
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
    {
        "title": "GFF/FASTA Genome Set",
        "app": "kb_uploadmethods/batch_import_genome_from_staging",
        "output_type": ["KBaseSearch.GenomeSet"],
    },
]

mapping[ZIP] = [
    {
        "title": "Decompress/Unpack",
        "app": "kb_uploadmethods/unpack_staging_file",
        "output_type": [],
    }
]
mapping[CSV] = \


    ["sample_uploader/import_samples"]
mapping[EXCEL] = ["sample_uploader/import_samples"]
mapping[TSV] = ["kb_uploadmethods/import_tsv_as_expression_matrix_from_staging"]

extension_to_type_mapping = defaultdict(list)
extension_to_app_mapping = defaultdict(list)
for datatype in type_to_extension_mapping:
    for file_extension in type_to_extension_mapping[datatype]:
        extension_to_type_mapping[file_extension.lower()].append(datatype)
        app = mapping[datatype]
        extension_to_app_mapping[file_extension.lower()].append(app)

extension_to_type_mapping = extension_to_type_mapping
extension_to_app_mapping = extension_to_app_mapping

import json

print("Extension to type mapping")
print(json.dumps(extension_to_type_mapping, indent=2))

print("Extension to app mapping")

print(json.dumps(extension_to_app_mapping, indent=2))
