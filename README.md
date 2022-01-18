# staging_service


In order to setup local development, you must have docker installed and if you want to run it locally you must have python 3.9.6 or greater installed


# setup

make a folder called /data as well as inside that /bulk and inside that a folder for any usernames you wish it to work with

data
    -bulk
        -username
        -username


if you want to run locally you must install requirements.txt for python3

# running

to run locally run /deployment/bin/entrypoint.sh

to run inside docker run /run_in_docker.sh

# tests

* to test use ./run_tests.sh
* requires python 3.9.6 or higher
* requires installation on mac of libmagic `brew install libmagic`



# debugging

Included configurations for the Visual Studio Code debugger for python that mirror what is in the entrypoint.sh and testing configuration to run locally in the debugger, set breakpoints and if you open the project in VSCode the debugger should be good to go. The provided configurations can run locally and run tests locally

# expected command line utilities
to run locally you will need all of these utils on your system: tar, unzip, zip, gzip, bzip2, md5sum, head, tail, wc

in the docker container all of these should be available

# API

all paths should be specified treating the user's home directory as root

## Test Service

**URL** : `ci.kbase.us/services/staging_service/test-service`

**local URL** : `localhost:3000/test-service`

**Method** : `GET`

### Success Response

**Code** : `200 OK`

**Content example**

```
This is just a test. This is only a test.
```
## Test Auth

**URL** : `ci.kbase.us/services/staging_service/test-auth`

**local URL** : `localhost:3000/test-auth`

**Method** : `GET`

**Headers** : `Authorization: <Valid Auth token>`

### Success Response

**Code** : `200 OK`

**Content example**

```
I'm authenticated as <username>
```

### Error Response

**Condition** : if authentication is incorrect

**Code** : `401 Unauthorized`

**Content** :
```
Error Connecting to auth service ...
```
**Code** : `400 Bad Request`

**Content**
```
Must supply token
```

## File Lifetime
**URL** : `ci.kbase.us/services/staging_service/file-lifetime`
**local URL** : `localhost:3000/file-lifetime`

**Method** : `GET`

### Success Response

**Code** : `200 OK`

**Content example**
number of days a file will be held for in staging service before being deleted
this is not actually handled by the server but is expected to be performed by a cron job which shares the env variable read here

```
90
```

## List Directory
defaults to not show hidden dotfiles

**URL** : `ci.kbase.us/services/staging_service/list/{path to directory}`

**URL** : `ci.kbase.us/services/staging_service/list/{path to directory}?showHidden={True/False}`

**local URL** : `localhost:3000/list/{path to directory}`

**local URL** : `localhost:3000/list/{path to directory}?showHidden={True/False}`

**Method** : `GET`

**Headers** : `Authorization: <Valid Auth token>`

### Success Response

**Code** : `200 OK`

**Content example**

```json
[
    {
        "name": "testFolder",
        "path": "nixonpjoshua/testFolder",
        "mtime": 1510949575000,
        "size": 96,
        "isFolder": true
    },
    {
        "name": "testfile",
        "path": "nixonpjoshua/testfile",
        "mtime": 1510949629000,
        "size": 335,
        "isFolder": false
    }
]
```
### Error Response

**Condition** : if authentication is incorrect

**Code** : `401 Unauthorized`

**Content** :
```
Error Connecting to auth service ...
```
**Code** : `400 Bad Request`

**Content**
```
Must supply token
```

**Code** : `404 Not Found`

**Content** :
```
path <username>/<incorrect path> does not exist
```

## Download file

**URL** : `ci.kbase.us/services/staging_service/download/{path to file}`

**URL** : `ci.kbase.us/services/staging_service/download/{path to file}`

**local URL** : `localhost:3000/download/{path to file}`

**local URL** : `localhost:3000/download/{path to file}`

**Method** : `GET`

**Headers** : `Authorization: <Valid Auth token>`

### Success Response

**Code** : `200 OK`
**Content** : `<file content>`

### Error Response

**Condition** : if authentication is incorrect

**Code** : `401 Unauthorized`

**Content** :
```
Error Connecting to auth service ...
```
**Code** : `400 Bad Request`

**Content**
```
Must supply token
```

**Code** : `400 Bad Request`

**Content** :
```
<username>/<incorrect path> is a directory not a file
```

**Code** : `404 Not Found`

**Content** :
```
path <username>/<incorrect path> does not exist
```

## Search files and folders
defaults to not show hidden dotfiles

**URL** : `ci.kbase.us/services/staging_service/search/{search query}`

**URL** : `ci.kbase.us/services/staging_service/search/{search query}?showHidden={True/False}`

**local URL** : `localhost:3000/search/{search query}`

**local URL** : `localhost:3000/search/?showHidden={True/False}`

**Method** : `GET`

**Headers** : `Authorization: <Valid Auth token>`

### Success Response

**Code** : `200 OK`

**Content example**

```json
[
    {
        "name": "testfile",
        "path": "nixonpjoshua/testfile",
        "mtime": 1510949629000,
        "size": 335,
        "isFolder": false
    },
    {
        "name": "testFolder",
        "path": "nixonpjoshua/testFolder",
        "mtime": 1510949575000,
        "size": 96,
        "isFolder": true
    },
    {
        "name": "testinnerFile",
        "path": "nixonpjoshua/testFolder/testinnerFile",
        "mtime": 1510949575000,
        "size": 0,
        "isFolder": false
    }
]
```
### Error Response

**Condition** : if authentication is incorrect

**Code** : `401 Unauthorized`

**Content** :
```
Error Connecting to auth service ...
```
**Code** : `400 Bad Request`

**Content**
```
Must supply token
```

## File and Folder Metadata

**URL** : `ci.kbase.us/services/staging_service/metadata/{path to file or folder}`

**local URL** : `localhost:3000/metadata/{path to file or folder}`

**Method** : `GET`

**Headers** : `Authorization: <Valid Auth token>`

### Success Response

**Code** : `200 OK`

**Content example**

```json
{
    "name": "testFolder",
    "path": "nixonpjoshua/testFolder",
    "mtime": 1510949575000,
    "size": 96,
    "isFolder": true
}
```

```json
{
    "md5": "73cf08ad9d78d3fc826f0f265139de33",
    "lineCount": "13",
    "head": "there is stuff in this file\nthere is stuff in this file\nthere is stuff in this file\nthere is stuff in this file\nthere is stuff in this file\nthere is stuff in this file\nthere is stuff in this file\nstuff at the bottom\nstuff at the bottom\nstuff at the bottom",
    "tail": "there is stuff in this file\nthere is stuff in this file\nthere is stuff in this file\nstuff at the bottom\nstuff at the bottom\nstuff at the bottom\nstuff at the bottom\nstuff at the bottom\nstuff at the bottom\nstuff at the bottom",
    "name": "testFile",
    "path": "nixonpjoshua/testFile",
    "mtime": 1510949629000,
    "size": 335,
    "isFolder": false
}
```
### Error Response

**Condition** : if authentication is incorrect

**Code** : `401 Unauthorized`

**Content** :
```
Error Connecting to auth service ...
```
**Code** : `400 Bad Request`

**Content**
```
Must supply token
```

**Code** : `404 Not Found`

**Content** :
```
path <username>/<incorrect path> does not exist
```

## Upload File

**URL** : `ci.kbase.us/services/staging_service/upload`

**local URL** : `localhost:3000/upload`

**Method** : `POST`

**Headers** : `Authorization: <Valid Auth token>`

**Body constraints**

first element in request body should be

destPath: {path file should end up in}

second element in request body should be multipart file data

uploads: {multipart file}

Files starting with whitespace or a '.' are not allowed

### Success Response

**Code** : `200 OK`

**Content example**

```json
[
    {
        "name": "fasciculatum_supercontig.fasta",
        "path": "nixonpjoshua/fasciculatum_supercontig.fasta",
        "mtime": 1510950061000,
        "size": 31536508,
        "isFolder": false
    }
]
```
### Error Response

**Condition** : if authentication is incorrect

**Code** : `401 Unauthorized`

**Content** :
```
Error Connecting to auth service ...
```
**Code** : `400 Bad Request`

**Content**
```
Must supply token
```

## Define/Create UPA for file which has been imported

**URL** : `ci.kbase.us/services/staging_service/define-upa/{path to imported file}`

**local URL** : `localhost:3000/define-upa/{path to imported file}`

**Method** : `POST`

**Headers** : `Authorization: <Valid Auth token>`

**Body constraints**

first element in request body should be

UPA: {the actual UPA of imported file}

### Success Response

**Code** : `200 OK`

**Content example**

```
successfully update UPA <UPA> for file <Path>
```
### Error Response

**Condition** : if authentication is incorrect

**Code** : `401 Unauthorized`

**Content** :
```
Error Connecting to auth service ...
```
**Code** : `400 Bad Request`

**Content**
```
Must supply token
```

**Code** : `400 Bad Request`

**Content**
```
must provide UPA field in body
```


## Delete file or folder (will delete things contained in folder)

**URL** : `ci.kbase.us/services/staging_service/delete/{path to file or folder}`

**local URL** : `localhost:3000/delete/{path to file or folder}`

**Method** : `DELETE`

**Headers** : `Authorization: <Valid Auth token>`

### Success Response

**Code** : `200 OK`

**Content example**

```
successfully deleted UPA <Path>
```
### Error Response

**Condition** : if authentication is incorrect

**Code** : `401 Unauthorized`

**Content** :
```
Error Connecting to auth service ...
```
**Code** : `400 Bad Request`

**Content**
```
Must supply token
```

**Code** : `404 Not Found`

**Content**
```
could not delete <Path>
```

**Code** : `403 Forbidden`

**Content**
```
cannot delete home directory
```
```
cannot delete protected file
```

## Move/rename a file or folder

**URL** : `ci.kbase.us/services/staging_service/mv/{path to file or folder}`

**local URL** : `localhost:3000/mv/{path to file or folder}`

**Method** : `PATCH`

**Headers** : `Authorization: <Valid Auth token>`

**Body constraints**

first element in request body should be

newPath : {the new location/name for file or folder}

### Success Response

**Code** : `200 OK`

**Content example**

```
successfully moved <path> to <newPath>
```
### Error Response

**Condition** : if authentication is incorrect

**Code** : `401 Unauthorized`

**Content** :
```
Error Connecting to auth service ...
```
**Code** : `400 Bad Request`

**Content**
```
Must supply token
```

**Code** : `400 Bad Request`

**Content**
```
must provide newPath field in body
```

**Code** : `403 Forbidden`

**Content**
```
cannot rename home or move directory
```
```
cannot rename or move protected file
```
**Code**: `409 Conflict`

**Content**
```
<newPath> allready exists
```

## Decompress various archive formats
supported archive formats are:
.zip, .ZIP, .tar.gz, .tgz, .tar.bz, .tar.bz2, .tar, .gz, .bz2, .bzip2
**URL** : `ci.kbase.us/services/staging_service/decompress/{path to archive`

**local URL** : `localhost:3000/decompress/{path to archive}`

**Method** : `PATCH`

**Headers** : `Authorization: <Valid Auth token>`

### Success Response

**Code** : `200 OK`

**Content example**

```
successfully decompressed <path to archive>
```
### Error Response

**Condition** : if authentication is incorrect

**Code** : `401 Unauthorized`

**Content** :
```
Error Connecting to auth service ...
```
**Code** : `400 Bad Request`

**Content**
```
Must supply token
```

**Code** : `400 Bad Request`

**Content**
```
cannot decompress a <file extension> file
```


## Add Globus ACL

After authenticating at this endpoint, AUTH is queried to get your filepath and globus id file for 
linking to globus.

**URL** : `ci.kbase.us/services/staging_service/add-acl`

**local URL** : `localhost:3000/add-acl`

**Method** : `GET`

**Headers** : `Authorization: <Valid Auth token>`

### Success Response

**Code** : `200 OK`

**Content example**

```
{
    "success": true,
    "principal": "KBase-Example-59436z4-z0b6-z49f-zc5c-zbd455f97c39",
    "path": "/username/",
    "permissions": "rw"
}
```
### Error Response

**Condition** : if authentication is incorrect

**Code** : `401 Unauthorized`

**Content** :
```
Error Connecting to auth service ...
```

**Condition** : If issue with Globus API or ACL Already Exists

**Code** : `500 Internal Server Error`

**Content**
```
{
    'success': False, 
    'error_type': 'TransferAPIError',
    'error': "Can't create ACL rule; it already exists",
    'error_code': 'Exists', 'shared_directory_basename': '/username/'
}
```

## Remove Globus ACL

After authenticating at this endpoint, AUTH is queried to get your filepath and globus id file for 
linking to globus.

**URL** : `ci.kbase.us/services/staging_service/remove-acl`

**local URL** : `localhost:3000/remove-acl`

**Method** : `GET`

**Headers** : `Authorization: <Valid Auth token>`

### Success Response

**Code** : `200 OK`

**Content example**

```
{
    "message": "{\n  \"DATA_TYPE\": \"result\",\n  \"code\": \"Deleted\",
    "message\": \"Access rule 'KBASE-examplex766ada0-x8aa-x1e8-xc7b-xa1d4c5c824a' deleted successfully\", 
    "request_id\": \"x2KFzfop05\",\n  \"resource\": \"/endpoint/KBaseExample2a-5e5b-11e6-8309-22000b97daec/access/KBaseExample-ada0-d8aa-11e8-8c7b-0a1d4c5c824a\"}",
    "Success": true
}
```
### Error Response

**Condition** : if authentication is incorrect

**Code** : `401 Unauthorized`

**Content** :
```
Error Connecting to auth service ...
```

**Condition** : If issue with Globus API or ACL Already Exists

**Code** : `500 Internal Server Error`

**Content**
```
{
    'success': False, 
    'error_type': 'TransferAPIError',
    'error': "Can't create ACL rule; it already exists",
    'error_code': 'Exists', 'shared_directory_basename': '/username/'
}
```

## Parse bulk specifications

This endpoint parses one or more bulk specification files in the staging area into a data
structure (close to) ready for insertion into the Narrative bulk import or analysis cell.

It can parse `.tsv`, `.csv`, and Excel (`.xls` and `.xlsx`) files. Templates for the currently
supported data types are available in the [templates](./import_specifications/templates)
directory of this repo. See the [README.md](./import_specifications/templates/README.md) file
for instructions on template usage.

See the [import specification ADR document](./docs/import_specifications.ADR.md) for design
details.

**URL** : `ci.kbase.us/services/staging_service/bulk_specification`

**local URL** : `localhost:3000/bulk_specification`

**Method** : `GET`

**Headers** : `Authorization: <Valid Auth token>`

### Success Response

**Code** : `200 OK`

**Content example**

```
GET bulk_specification/?files=file1.<ext>[,file2.<ext>,...]
```
`<ext>` is one of `csv`, `tsv`, `xls`, or `xlsx`.

Reponse:
```
{
    "types": {
        <type 1>: [
            {<spec.json ID 1>: <value for ID, row 1>, <spec.json ID 2>: <value for ID, row 1>, ...},
            {<spec.json ID 1>: <value for ID, row 2>, <spec.json ID 2>: <value for ID, row 2>, ...},
            ...
        ],
        <type 2>: [
            {<spec.json ID 1>: <value for ID, row 1>, <spec.json ID 2>: <value for ID, row 1>, ...},
            ...
        ],
        ...
    },
    "files": {
        <type 1>: {"file": "<username>/file1.<ext>", "tab": "tabname"},
        <type 2>: {"file": "<username>/file2.<ext>", "tab": null},
        ...
    }
}
```

* `<type N>` is a data type ID from the [Mappings.py](./staging_service/autodetect/Mappings.py)
  file and the Narrative staging area configuration file - it is a shared namespace between the
  staging service and Narrative to specify bulk applications, and has a 1:1 mapping to an
  app. It is determined by the first header line from the templates.
* `<spec.json ID N>` is the ID of an input parameter from a `KB-SDK` app's `spec.json` file.
  These are determined by the second header line from the templates and will differ
  by the data type.
* `<value for ID, row N>` is the user-provided value for the input for a given `spec.json` ID
  and import or analysis instance, where an import/analysis instance is effectively a row
  in the data file. Each data file row is provided in order for each type. Each row is
  provided in a mapping of `spec.json` ID to the data for the row. Lines > 3 in the templates are
  user-provided data, and each line corresponds to a single import or analysis.
  
### Error Response

Error reponses are of the general form:
```
{
    "errors": [
        {"type": <error code string>,
            ... other fields depending on the error code ...
        },
        ...
    ]
}
```

Existing error codes are currently:

* `cannot_find_file` if an input file cannot be found
* `cannot_parse_file` if an input file cannot be parsed
* `incorrect_column_count` if the column count is not as expected
    * For Excel files, this may mean there is a non-empty cell outside the bounds of the data area
* `multiple_specifications_for_data_type` if more than one tab or file per data type is submitted
* `no_files_provided` if no files were provided
* `unexpected_error` if some other error occurs

The HTTP code returned will be, in order of precedence:
* 400 if any error other than `cannot_find_file` or `unexpected_error` occurs
* 404 if at least one error is `cannot_find_file` but there are no 400-type errors
* 500 if all errors are `unexpected_error`

The per error type data structures are:

#### `cannot_find_file`

```
{
    "type": "cannot_find_file",
    "file": <filepath>
}
```

#### `cannot_parse_file`

```
{
    "type": "cannot_parse_file",
    "file": <filepath>,
    "tab": <spreadsheet tab if applicable, else null>,
    "message": <message regarding the parse error>
}
```

#### `incorrect_column_count`

```
{
    "type": "incorrect_column_count",
    "file": <filepath>,
    "tab": <spreadsheet tab if applicable, else null>,
    "message": <message regarding the error>
}
```

#### `multiple_specifications_for_data_type`

```
{
    "type": "multiple_specifications_for_data_type",
    "file_1": <filepath for first file>,
    "tab_1": <spreadsheet tab from first file if applicable, else null>,
    "file_2": <filepath for second file>,
    "tab_2": <spreadsheet tab for second file if applicable, else null>,
    "message": <message regarding the multiple specification error>
}
```

#### `no_files_provided`

```
{
    "type": "no_files_provided"
}
```

#### `unexpected_error`

```
{
    "type": "unexpected_error",
    "file": <filepath if applicable to a single file>
    "message": <message regarding the error>
}
```

## Write bulk specifications

This endpoint is the reverse of the parse bulk specifications endpoint - it takes a similar
data structure to that which the parse endpoint returns and writes bulk specification templates.

**URL** : `ci.kbase.us/services/staging_service/write_bulk_specification/`

**local URL** : `localhost:3000/write_bulk_specification/`

**Method** : `POST`

**Headers** :
* `Authorization: <Valid Auth token>`
* `Content-Type: Application/JSON`

### Success Response

**Code** : `200 OK`

**Content example**

```
POST write_bulk_specification/
{
    "output_directory": <staging area directory in which to write output files>,
    "output_file_type": <one of "CSV", "TSV", or "EXCEL">,
    "types": {
        <type 1>: {
            "order_and_display: [
                [<spec.json ID 1>, <display.yml name 1>],
                [<spec.json ID 2>, <display.yml name 2>],
                ...
            ],
            "data": [
                {<spec.json ID 1>: <value for ID, row 1>, <spec.json ID 2>: <value for ID, row 1>, ...},
                {<spec.json ID 1>: <value for ID, row 2>, <spec.json ID 2>: <value for ID, row 2>, ...}
                ...
            ]
        },
        <type 2>: {
            "order_and_display: [
                [<spec.json ID 1>, <display.yml name 1>],
                ...
            ],
            "data": [
                {<spec.json ID 1>: <value for ID, row 1>, <spec.json ID 2>: <value for ID, row 1>, ...},
                ...
            ]
        },
        ...
    }
}
```
* `output_directory` specifies where the output files should be written in the user's staging area.
* `output_file_type` specifies the format of the output files.
* `<type N>` is a data type ID from the [Mappings.py](./staging_service/autodetect/Mappings.py)
  file and the Narrative staging area configuration file - it is a shared namespace between the
  staging service and Narrative to specify bulk applications, and has a 1:1 mapping to an
  app. It is included in the first header line in the templates.
* `order_and_display` determines the ordering of the columns in the written templates, as well
  as mapping the spec.json ID of the parameter to the human readable name of the parameter in
  the display.yml file.
* `<spec.json ID N>` is the ID of an input parameter from a `KB-SDK` app's `spec.json` file.
  These are written to the second header line from the import templates and will differ
  by the data type.
* `data` contains any data to be written to the file as example data, and is analagous to the data
  structure returned from the parse endpoint. To specify that no data should be written to the
  template provide an empty list.
* `<value for ID, row N>` is the value for the input for a given `spec.json` ID
  and import or analysis instance, where an import/analysis instance is effectively a row
  in the data file. Each data file row is provided in order for each type. Each row is
  provided in a mapping of `spec.json` ID to the data for the row. Lines > 3 in the templates are
  user-provided data, and each line corresponds to a single import or analysis.

Reponse:
```
{
    "output_file_type": <one of "CSV", "TSV", or "EXCEL">,
    "files": {
        <type 1>: <staging service path to file containg data for type 1>,
        ...
        <type N>: <staging service path to file containg data for type N>,
    }
}
```

* `output_file_type` has the same definition as above.
* `files` contains a mapping of each provided data type to the output template file for that type.
  In the case of Excel, all the file paths will be the same since the data types are all written
  to different tabs in the same file.
  
### Error Response

Method specific errors have the form:

```
{"error": <error message>}
```
The error code in this case will be a 4XX error.

The AioHTTP server may also return built in errors that are not in JSON format - an example of
this is overly large (> 1MB) request bodies.


## Get Importer Mappings

This endpoint returns:
1) a mapping between a list of files and predicted importer apps, and
2) a file information list that includes the input file names split between the file prefix and
   the file suffix, if any, that was used to determine the file -> importer mapping, and a list
   of file types based on the file suffix. If a file has a suffix that does not match
   any mapping (e.g. `.sys`), the suffix will be `null`, the prefix the entire file name, and
   the file type list empty.

For example,
 * if we pass in nothing we get a response with no mappings
 * if we pass in a list of files, such as ["file1.fasta", "file2.fq", "None"], we would get back a
   response that maps to Fasta Importers and FastQ Importers, with a weight of 0 to 1 
   which represents the probability that this is the correct importer for you.
 * for files for which there is no predicted app, the return is a null value
 * this endpoint is used to power the dropdowns for the staging service window in the Narrative

**URL** : `ci.kbase.us/services/staging_service/importer_mappings`

**local URL** : `localhost:3000/importer_mappings`

**Method** : `POST`

**Headers** : Not Required

### Success Response

**Code** : `200 OK`

**Content example**

```
data = {"file_list": ["file1.txt", "file2.zip", "file3.gff3.gz"]}
    async with AppClient(config, username) as cli:
        resp = await cli.post(
            "importer_mappings/", data=data
        )
```
Response:
```
{
    "mappings": [
        null,
        [{
            "id": "decompress",
            "title": "decompress/unpack",
            "app_weight": 1,
        }],
        [{
            "app_weight": 1,
            "id": "gff_genome",
            "title": "GFF/FASTA Genome",
          },
         {
            "app_weight": 1,
            "id": "gff_metagenome",
            "title": "GFF/FASTA MetaGenome",
        }]
    ],
    "fileinfo": [
        {"prefix": "file1.txt", "suffix": null, "file_ext_type": []},
        {"prefix": "file2", "suffix": "zip", "file_ext_type": ["CompressedFileFormatArchive"]},
        {"prefix": "file3", "suffix": "gff3.gz", "file_ext_type": ["GFF"]}
    ]
}
```
### Error Response
**Code** : `400 Bad Request`

**Content**
```
must provide file_list field 
```

## Get importer filetypes

This endpoint returns information about the file types associated with data types and the file
extensions for those file types. It is primarily of use for creating UI elements describing
which file extensions may be selected when performing bulk file selections.

**URL** : `ci.kbase.us/services/staging_service/importer_filetypes`

**local URL** : `localhost:3000/importer_filetypes`

**Method** : `GET`

**Headers** : Not Required

### Success Response

**Code** : `200 OK`

**Content example**

```
GET importer_filetypes/
```
Response:
```
{
    "datatype_to_filetype": {
        <type 1>: [<file type 1>, ... <file type N>],
        ...
        <type M>: [<file type 1>, ... <file type N>],
    },
    "filetype_to_extensions": {
        <file type 1>: [<extension 1>, ..., <extension N>],
        ...
        <file type M>: [<extension 1>, ..., <extension N>],
    }
}
```

* `<type N>` is a data type ID from the [Mappings.py](./staging_service/autodetect/Mappings.py)
  file and the Narrative staging area configuration file - it is a shared namespace between the
  staging service and Narrative to specify bulk applications, and has a 1:1 mapping to an
  import app. It is included in the first header line in the templates.
* `<file type N>` is a file type like `FASTA` or `GENBANK`. The supported file types are listed
  below.
* `<extension N>` is a file extension like `*.fa` or `*.gbk`.

# Autodetect App and File Type IDs

## App type IDs

These are the currently supported upload app type IDs:

```
fastq_reads_interleaved
fastq_reads_noninterleaved
sra_reads
genbank_genome
gff_genome
gff_metagenome
expression_matrix
media
fba_model
assembly
phenotype_set
sample_set
metabolic_annotation
metabolic_annotation_bulk
escher_map
decompress
```

Note that decompress is only returned when no other file type can be detected from the file
extension.

## File type IDs

These are the currently supported file type IDs. These are primarily useful for apps that take
two different file types, like GFF/FASTA genomes.

```
FASTA
FASTQ
SRA
GFF
GENBANK
SBML
JSON
TSV
CSV
EXCEL
CompressedFileFormatArchive
```
