"""
* Save this indirectly as a json file
* Save this indirectly as a yaml file
* Serve that generated content from memory

"""
import json
from collections import defaultdict
import yaml

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
        "title": "Genbank Genome",
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
        "output_type": [None],
    }
]
mapping[CSV] = [
    {
        "title": "Import Samples",
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
    {
        "title": "Attribute Mapping",
        "app": "kb_uploadmethods/import_attribute_mapping_from_staging",
        "output_type": ["KBaseExperiments.AttributeMapping"],
    },
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
extension_to_app_mapping = defaultdict(list)
for datatype in type_to_extension_mapping:
    for file_extension in type_to_extension_mapping[datatype]:
        extension_to_type_mapping[file_extension.lower()].append(datatype)
        app = mapping[datatype]
        extension_to_app_mapping[file_extension.lower()].extend(app)

extension_to_type_mapping = extension_to_type_mapping
extension_to_app_mapping = extension_to_app_mapping

print("Extension to type mapping")
with open("./autodetect/extension_to_type.json", "w") as f:
    print(json.dumps(extension_to_type_mapping, indent=2))
    json.dump(obj=extension_to_type_mapping, fp=f, indent=2)

print("Extension to app mapping")
with open("./autodetect/extension_to_app.json", "w") as f:
    print(json.dumps(extension_to_app_mapping, indent=2))
    json.dump(obj=extension_to_app_mapping, fp=f, indent=2)
