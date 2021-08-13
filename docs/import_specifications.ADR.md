# Import Specifications Architecture Design Record

This document specifies the design for handling import specifications in the Staging Service (StS).
An upload specification is an Excel, CSV, or TSV file that contains instructions for how
to import one or more files in the staging area to KBase as KBase data types.

## Resources

* [The original strategy document for this approach](https://docs.google.com/document/d/1ocmZVBlTzAh_cdZaWGRwIbAuH-mcPRZFdhcwRhAfzxM/edit)
  * Readable for everyone that has access to the KBase Google Docs folder
  * The document contains short descriptions of future projects not included in this work,
    such as generating template files on the fly and rich templates.

## Front end changes

The design introduces a new StS data type, `upload_specification`. The FE's current 
behavior is to display any data types returned from the StS in the file dropdown, but silently
ignore user-selected files for which the selected data type is unknown to the narrative, a bug.
The FE will be updated to ignore unknown data types returned from the StS, allowing for phased,
non-lockstep upgrades. This work is not included in this project, but will be in a future FE
project.

## Upload specification input files

Input file formats may be Excel, CSV, or TSV. An example CSV file structure for GFF/FASTA uploads
is below:

```
Data type:, gff_metagenome, Version:, 1
fasta_file, gff_file, genome_name, source, release, genetic_code, generate_missing_genes
FASTA File Path, GFF3 File Path, Metagenome Object Name, Source of metagenome, Release or Version of the Source Data, Genetic Code for protein translation, Spoof Genes for parentless CDS
mygenome.fa, mygenome.gff3, mygenomeobject, , , 11, 0
mygenome2.fa, mygenome2.gff3, mygenomeobject2, yermumspoo, 30456, 11, 1
...
```

The file, by row, is:
1. The data type, in this case `gff_metagenome`, and the version, in this case 1. The data type is
  from the list in the
  [Mappings.py](https://github.com/kbase/staging_service/blob/master/staging_service/autodetect/Mappings.py)
  file in the StS. The Narrative is expected to understand these types and map them to uploader
  apps. The version allows us to update the file format and increment the version, allowing
  backwards compatibility - the staging service can process the file appropriately depending on
  the version number.
2. The IDs of the app inputs from the `spec.json` file. 
3. The corresponding human readable names of the app inputs from the `display.yaml` file.
4. (and beyond) Import specifications. Each line corresponds to a single import.

For Excel files, the first two rows may be hidden in any provided templates. Additionally,
Excel files may contain multiple data types, one per tab. Empty tabs will be ignored, and tabs
that don't match the expected structure will be treated as an error.

As part of this project we will deliver:
1. CSV templates for each in scope app (e.g. the first 3 lines of the example file)
2. An Excel template containing a tab for each in scope app
3. A `README.md` file explaining how to use the templates.
   * The `README.md` should include a link to rich import specification documentation on the KBase
     website once it is developed.
   * Note: cover booleans / checkboxes which are not intuitive. 0 will indicate unchecked, and 1
     checked. These values may show up as strings in the API, and the consumer will be expected to
     handle conversion appropriately.

These files will reside in the StS repo. As part of the front end effort, some means of
delivering the templates and instructions to users will be developed.

Currently, for all in scope apps, the inputs are all strings, numbers, or booleans. There are
no unusual inputs such as grouped parameters or dynamic lookups. Including future upload apps
with these features in CSV-based upload may require additional engineering.

Note that the endpoint will return individual data for each row, while the current front end
only supports individual input files and output objects (this may be improved in a future update).
The front end will be expected to either
1. Ignore all parameters other than in the first entry in the return per type, or
2. Throw an error if parameters differ from the first entry.

## User operations

* The user uploads the import specification files to the staging area along with all the files
  inluded in the specification. 
* The user selects the `Import Specification` type for the specification files.
  * The user may also select other files in the staging area to include in the import along
    with the files listed in the specification.
    * The user *does not* have to select any files included in the specification.
* The user clicks `Import Selected`.

As such, a new type must be added to the StS: `import_specification` with the title
`Import Specification`. *Nota bene*: It may be preferable to have the Narrative specify the
titles to display in the staging area dropdown rather than the StS.

## Narrative Bulk Import cell operations

When the narrative sees an `import_specification` data type, it calls out to the StS
endpoint detailed below to get the parsed specifications, and then initializes the bulk import
cell with those specifications.

## Staging service import specification endpoint

The StS endpoint responds to an HTTP GET with a file list in a `files` URL parameter. It is
extremely unlikely that there will be a large enough set of data types that URL length limits
will be reached so this seems adequate. The StS will respond with the contents of the files
parsed into a structure that is similar to that of the input spec, mapped by data type:

```
Headers:
Authorization: <KBase token>

GET /bulk_specification/?files=<file1.csv[,file2.csv,...]>

Response:
{"types": {
    "gff_metagenome": [
        {"fasta_file": "mygenome.fa",
         "gff_file": "mygenome.gff3",
         "genome_name": "mygenomeobject",
         "source": null,
         "release": null,
         "genetic_code: 11,
         "generate_missing_genes: 0
         },
        {"fasta_file": "mygenome2.fa",
         "gff_file": "mygenome2.gff3",
         "genome_name": "mygenomeobject2",
         "source": "yermumspoo",
         "release": 30456,
         "genetic_code: 11,
         "generate_missing_genes: 1
         },
         ...
    ],
    "sra_reads": [
        ...
    ]
    ...
}
```

The order of the input structures MUST be the same as the order in the input files.

Notably, the service will provide the contents of the files as is and will not perform most error
checking, including for missing or unknown input parameters. Most error checking will be performed
in the bulk import cell configuration tab like other uploads, allowing for a consistent user
experience.

### Error handling

The StS will return errors on a (mostly) per input file basis, with a string error code for
each error type. Currently the error types are:

* `cannot_find_file` if an input file cannot be found
* `cannot_parse_file` if an input file cannot be parsed
* `illegal_file_name` if an illegal file name is provided
* `multiple_specifications_for_data_type` if more than one tab or file per data type is submitted
* `no_files_provided` if no files were provided
* `unexpected_error` if some other error occurs

The HTTP code returned will be, in order of precedence:

* 400 if any error other than `cannot_find_file` or `unexpected_error` occurs
* 404 if at least one error is `cannot_find_file` but there are no 400-type errors
* 500 if all errors are `unexpected_error`

The general structure of the error response is:

```
{"errors": [
    {"type": <error code string>,
        ... other fields depending on the error code ...
    },
    ...
]}
```

The individual error structures per error type are as follows:

#### `cannot_find_file`

```
{"type": "cannot_find_file",
 "file": <filepath>
}
```

#### `cannot_parse_file`

```
{"type": "cannot_parse_file",
 "file": <filepath>,
 "tab": <spreadsheet tab if applicable, else null>,
 "message": <message regarding the parse error>
}
```

The service will check that the data type is valid and that rows >=2 all have the same number of
entries, but will not do further error checking.

Note in this case the service MUST log the stack trace along with the filename for each invalid
file.

#### `illegal_file_name`

```
{"type": "illegal_file_name",
 "message": <message regarding the illegal name>,
 "file": <filepath>
}
```

The `file` key will not be provided if there is a `null` filename provided. This is currently
impossible based on the API but we note it here in case a JSON body based API is provided in the
future.

#### `multiple_specifications_for_data_type`

```
{"type": "multiple_specifications_for_data_type",
 "file_1": <filepath for first file>,
 "tab_1": <spreadsheet tab from first file if applicable, else null>,
 "file_2": <filepath for second file>,
 "tab_2": <spreadsheet tab for second file if applicable, else null>,
 "message": <message regarding the multiple specification error>
}
```

#### `no_files_provided`

```
{"type": "no_files_provided"}
```

#### `unexpected_error`

```
{"type": "unexpected_error",
 "file": <filepath if applicable to a single file>
 "message": <message regarding the error>
}
```

Note in this case the service MUST log the stack trace along with the filename for each error.

## Alternatives explored

* We considered parsing the files in the Narrative backend (pulling the files as is from the StS)
  but the current design allows other services and UIs reusing the parsing code. There doesn't
  otherwise seem to be a strong reason to include the code one place or the other so we decided
  to include it in the StS.

## Questions

* Should it be an error to submit multiple files or tabs for the same type? If not,
  how should the different files be denoted and ordered?
  * This has follow on effect for how spreadsheet type views in the UI should be displayed.
  * A: For the MVP disallow submitting more than one file / tab per type. Post release we'll
    find out if this is a use case that users care about.
* Should we disallow filenames with commas? They may cause problems with the new endpoint.
  * A: Disallow commas, the same way we disallow files staring with whitespace or periods.
* Should we strictly enforce a column count for every row in xSV files?
  * Not enforcing a count makes it somewhat easier for users to fill in the data - they don't
    need to add extraneous commas or tabs to the end of the line.
  * Enforcing a count makes it less likely that a user will commit silent counting errors if
    there are many empty entries between items in a line.
  * A: Enforce a column count to prevent user errors.

## Addendum: dynamic parameter lookup

Dynamic scientific name to taxon lookup may be added to the Genbank (and the currently
out of scope, but trivial to add GFF/FASTA Genome) importer in the near future. If that occurs,
for the purpose of xSV upload the user will be expected to provide the entire, correct,
scientific name as returned from the taxon API. 

* The user could get this name by starting a genome upload and running the query from the 
  import app cell configuration screen.
  * This will be documented in the README.md for the template files.
* As part of the UI work we could theoretically provide a landing page for looking up valid
  scientific names.
* Presumably the UI would need to run the dynamic query and report an error to the user if the
  dynamic service returns 0 or > 1 entries.
* Providing the scientific name vs. the taxon api seems simpler because the machinery already 
  exists to perform the query and is part of the spec.
* Expect these plans to change as it becomes more clear how dynamic fields will work in the
  context of bulk upload.