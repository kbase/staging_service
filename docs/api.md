
# API

- all paths should be specified treating the user's home directory as root

- The url base, in an actualy deployment, will be:
  - `https://ci.kbase.us` for CI
  - `https://next.kbase.us` for Next
  - `https://appdev.kbase.us` for Appdev
  - `https://kbase.us` for Production

- The base path in all environments is `/services/staging_service`

- All api paths will be suffixed to the url base and base path. For example:

    `https://ci.kbase.us/services/staging_service/file-lifetime`
    will invoke the
    `file-lifetime` endpoint, which returns the number of days a file will be retained.

- For local usage (i.e. spinning the service up locally)
  - the base url is `http://localhost:3000`
  - the base path is not required
  - e.g. `http://localhost:3000/file-lifetime`

- For endpoints that require authorization, the `Authorization` header must be supplied,
  with the value a KBase auth token.

## Test Service

`GET /test-service`

Returns a fixed text response. Used to determine if the service is running?

> TODO: we probably don't need this endpoint

### Success Response

`200 OK`

#### Example

```text
This is just a test. This is only a test.
```

## Test Auth

`GET /test-auth`

Returns a text response indicating that the

### Headers

- `Authorization: <KBase Auth token>`

### Success Response

`200 OK`

`Content-Type: text/plain`

#### Example

```text
I'm authenticated as <username>
```

### Error Responses

The [common responses for an authorized request](#common-authorization-error-responses)

## File Lifetime

`GET /file-lifetime`

Number of days a file will be held for in staging service before being deleted.

This is not actually handled by the server but is expected to be performed by a cron job
which shares the env variable read here.

### Success Response

`200 OK`

#### Content

`text/plain`

#### Example

```text
90
```

## List Directory

`GET /list/{path to directory}?[showHidden={True/False}]`

Returns a JSON Array containing entries for each file and folder within the provided directory.

Defaults to not show hidden dotfiles.

### Headers

`Authorization: <Kbase Auth token>`

### Success Response

`200 OK`

### Example

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

### Error Responses

The [common responses for an authorized request](#common-authorization-error-responses)

#### `404 Not Found`

Results if the requested path is not found for the user associated with the
Authorization.

##### Content

`text/plain`

```text
path <username>/<incorrect path> does not exist
```

## Download file

`GET /download/{path to file}`

Returns the request file.

### Headers

- `Authorization: <KBase auth token>`

### Success Response

#### `200 OK`

##### Content

`application/octet-stream`

The contents of the file are returned as the entire body of the response

### Error Responses

The [common responses for an authorized request](#common-authorization-error-responses)

#### `400 Bad Request`

Returned if the requested file is a directory, not a file.

##### Content

`text/plain`

```text
<username>/<incorrect path> is a directory not a file
```

#### `404 Not Found`

The file does not exist

##### Content

`text/plain`

```text
path <username>/<incorrect path> does not exist
```

## Search files and folders

`GET /search/{search query}?[showHidden={True/False}]`

Returns a list of files for the user identified by the Authorization, and matching the
given query text

defaults to not show hidden dotfiles

> TODO: explain how the search works!

### Headers

- `Authorization: <Valid Auth token>`

### Success Response

#### `200 OK`

##### Content

`application/json`

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

### Error Responses

The [common responses for an authorized request](#common-authorization-error-responses)

## File and Folder Metadata

`GET /metadata/{path to file or folder}`

### Headers

- `Authorization: <KBase Auth token>`

### Success Response

#### `200 OK`

If the file or directory is found, a Metadata object is returned

##### Content

`application/json`

##### Examples

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

The [common responses for an authorized request](#common-authorization-error-responses)

#### `404 Not Found`

##### Content

`text/plain`

```text
path <username>/<incorrect path> does not exist
```

## Upload File

`POST /upload`

This most important endpoint is designed to receive one or more files in a `POST`
request sending a `multipart/form-data` body.

The body format is described in more detail below.

The response is a JSON object containing file metadata.

> This might seem a bit of an odd choice, and does complicate the API. It was chosen, I
> belive because the Narrative front-end component handling the submission of file
> uploads supports `multipart/form-data`, or it  may be because historically the first
> front-end implementation was a form itself, as HTML forms will send as
> `mutlipart/form-data` if a file control is used to select a file.
>
> The current front-end implementation does not require this, although it does support
> it, so I would suggest that in the future we refactor to be a simple binary body, with
> the filename specified in the url search (query param).

### Headers

- `Authorization: <Valid Auth token>`
- `Content-Type: multipart/form-data`

### Body

The multpart form-data format supports sending of multiple form fields, each with their
own metadata as well as body.

The service requires that two fields be present in the specified order:

- `destPath` - path file should end up in
- `uploads` - the file itself.

Filenames starting with whitespace or a '.' are not allowed

The `destPath` field contains the path at which the file should be created. It will
probably have been set based on the path of the file chosen for upload in the Narrative
interface (although the service API is agnostic about the how and why.)

The `uploads` field will contain a binary representation of the file. The file binary
content will be literaly copied into the destination file, with no encoding or validation.

#### Example

```text
------WebKitFormBoundaryA0xgUu1fi1whAcSB
Content-Disposition: form-data; name="destPath"

/
------WebKitFormBoundaryA0xgUu1fi1whAcSB
Content-Disposition: form-data; name="uploads"; filename="foo.csv"
Content-Type: text/markdown

[binary content excluded]
------WebKitFormBoundaryA0xgUu1fi1whAcSB--
```

In this example, the `destPath` is `/`, indicating that the file will be created in the
root directory of the user's staging area.

The `uploads` field would contain the file's binary content. Note that the field
metadata includes the "filename" property indicating that the target file
name is `"foo.csv"`.

### Success Response

`200 OK`

A successful response will return a JSON object containing a metadata description of the
file.

#### Content

`application/json`

```json
{
  "$schema": "http://json-schema.org/draft-04/schema#",
  "type": "array",
  "items": [
    {
      "type": "object",
      "properties": {
        "name": {
          "type": "string"
        },
        "path": {
          "type": "string"
        },
        "mtime": {
          "type": "integer"
        },
        "size": {
          "type": "integer"
        },
        "isFolder": {
          "type": "boolean"
        }
      },
      "required": [
        "name",
        "path",
        "mtime",
        "size",
        "isFolder"
      ]
    }
  ]
}
```

#### Example

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

The [common responses for an authorized request](#common-authorization-error-responses)

## Define/Create UPA for file which has been imported

`POST /define-upa/{path to imported file}`

### Headers

- `Authorization: <KBase Auth token>`
- `Content-Type: application/json`

### Body

The POST request body contains an object whose sole (??) property contains the `upa` to
associate with the provided file.

#### Schema

```json
{
  "$schema": "http://json-schema.org/draft-04/schema#",
  "type": "object",
  "properties": {
    "upa": {
      "type": "string",
      "description": "the actual UPA of imported file"
    }
  },
  "required": [
    "upa"
  ]
}
```

#### Example

```json
{
    "upa": "123.4.5"
}
```

### Success Response

`200 OK`

#### Headers

- `Content-Type: text/plain`

#### Body

```text
successfully update UPA <UPA> for file <Path>
```

### Error Responses

The [common responses for an authorized request](#common-authorization-error-responses)

#### `400 Bad Request`

UPA missing

##### Content

`text/plain`

```text
must provide UPA field in body
```

## Delete file or folder (will delete things contained in folder)

`DELETE /delete/{path to file or folder}`

### Headers

- `Authorization: <KBase Auth token>`

### Success Response

`200 OK`

#### Headers

- `Content-Type: text/plain`

#### Body

```text
successfully deleted UPA <Path>
```

### Error Response

The [common responses for an authorized request](#common-authorization-error-responses)

#### `403 Forbidden`

##### Headers

- `Content-Type: text/plain`

##### Content

```text
cannot delete home directory
```

```text
cannot delete protected file
```

or other file access errors.

#### `404 Not Found`

##### Headers

- `Content-Type: text/plain`

##### Body

```text
could not delete <Path>
```

## Move/rename a file or folder

`PATCH /mv/{path to file or folder}`

### Headers

- `Authorization: <KBase Auth token>`
- `Content-Type: application/json`

### Body

#### Schema

```json
{
  "$schema": "http://json-schema.org/draft-04/schema#",
  "type": "object",
  "properties": {
    "newPath": {
      "type": "string",
      "description": "the new location/name for file or folder"
    }
  },
  "required": [
    "newPath"
  ]
}
```

#### Example

```json
{
    "newPath": "/foo/bar"
}
```

### Success Response

`200 OK`

#### Headers

- `Content-Type: text/plain`

#### Body

```text
successfully moved <path> to <newPath>
```

### Error Response

The [common responses for an authorized request](#common-authorization-error-responses)

#### `400 Bad Request`

If the newPath field is missing in the content body

##### Headers

- `Content-Type: text/plain`

##### Body

```text
must provide newPath field in body
```

#### `403 Forbidden`

##### Headers

- `Content-Type: text/plain`

##### Body

```text
cannot rename home or move directory
```

```text
cannot rename or move protected file
```

#### `409 Conflict`

##### Headers

- `Content-Type: text/plain`

##### Body

```text
<newPath> already exists
```

## Decompress various archive formats

`PATCH /decompress/{path to archive}`

supported archive formats are:
.zip, .ZIP, .tar.gz, .tgz, .tar.bz, .tar.bz2, .tar, .gz, .bz2, .bzip2

### Headers

- `Authorization: <KBase Auth token>`

### Success Response

`200 OK`

#### Headers

- `Content-Type: text/plain`

#### Body

```text
successfully decompressed <path to archive>
```

### Error Response

The [common responses for an authorized request](#common-authorization-error-responses)

#### `400 Bad Request`

##### Headers

- `Content-Type: text/plain`

##### Body

```text
cannot decompress a <file extension> file
```

## Add Globus ACL

`GET /add-acl`

After authenticating at this endpoint, AUTH is queried to get your filepath and globus
id file for linking to globus.

### Headers

- `Authorization: <KBase Auth token>`

### Success Response

`200 OK`

#### Headers

- `Content-Type: application/json`

#### Body

##### Schema

```json
{
  "$schema": "http://json-schema.org/draft-04/schema#",
  "type": "object",
  "properties": {
    "success": {
      "type": "boolean"
    },
    "principal": {
      "type": "string"
    },
    "path": {
      "type": "string"
    },
    "permissions": {
      "type": "string"
    }
  },
  "required": [
    "success",
    "principal",
    "path",
    "permissions"
  ]
}
```

##### Example

```json
{
    "success": true,
    "principal": "KBase-Example-59436z4-z0b6-z49f-zc5c-zbd455f97c39",
    "path": "/username/",
    "permissions": "rw"
}
```

### Error Response

The [common responses for an authorized request](#common-authorization-error-responses)

#### `500 Internal Server Error`

If issue with Globus API or ACL Already Exists

##### Headers

- `Content-Type: application/json`

##### Body

###### Schema

```json
{
  "$schema": "http://json-schema.org/draft-04/schema#",
  "type": "object",
  "properties": {
    "success": {
      "type": "boolean"
    },
    "error_type": {
      "type": "string"
    },
    "error": {
      "type": "string"
    },
    "error_code": {
      "type": "string"
    },
    "shared_directory_basename": {
      "type": "string"
    }
  },
  "required": [
    "success",
    "error_type",
    "error",
    "error_code",
    "shared_directory_basename"
  ]
}
```

###### Content (example)

```json
{
    "success": false, 
    "error_type": "TransferAPIError",
    "error": "Can't create ACL rule; it already exists",
    "error_code": "Exists", 
    "shared_directory_basename": "/username/"
}
```

## Remove Globus ACL

`GET /remove-acl`

After authenticating at this endpoint, AUTH is queried to get your filepath and globus
id file for linking to globus.

### Headers

- `Authorization: <Valid Auth token>`

### Success Response

`200 OK`

#### Headers

- `Content-Type: application/json`

#### Body

##### Schema

##### Content (example)

```json
{
    "message": "... message elided...",
    "Success": true
}
```

Note that the "message" is that returned by the globus api, and out of scope for
documentation here.

> TODO: we should provide our own message, or return the globus rZesponse data, but not
> return the globus response data (a json object) into a string and call it a message!

### Error Response

The [common responses for an authorized request](#common-authorization-error-responses)

#### `500 Internal Server Error`

An issue with Globus API or ACL Already Exists

##### Headers

- `Content-Type: application/json`

##### Body

####### Schema

```json
{
  "$schema": "http://json-schema.org/draft-04/schema#",
  "type": "object",
  "properties": {
    "success": {
      "type": "boolean"
    },
    "error_type": {
      "type": "string"
    },
    "error": {
      "type": "string"
    },
    "error_code": {
      "type": "string"
    },
    "shared_directory_basename": {
      "type": "string"
    }
  },
  "required": [
    "success",
    "error_type",
    "error",
    "error_code",
    "shared_directory_basename"
  ]
}
```

####### Content (example)

```json
{
    "success": false, 
    "error_type": "TansferAPIError",
    "error": "Can't create ACL rule; it already exists",
    "error_code": "Exists", 
    "shared_directory_basename": "/username/"
}
```

## Parse bulk specifications

`GET /bulk_specification/?files=file1.<ext>[,file2.<ext>,...]`

where `<ext>` is one of `csv`, `tsv`, `xls`, or `xlsx`.

This endpoint parses one or more bulk specification files in the staging area into a data
structure (close to) ready for insertion into the Narrative bulk import or analysis cell.

It can parse `.tsv`, `.csv`, and Excel (`.xls` and `.xlsx`) files. Templates for the
currently supported data types are available in the
[templates](./import_specifications/templates) directory of this repo. See the
[README.md](./import_specifications/templates/README.md) file for instructions on
template usage.

See the [import specification ADR document](./docs/import_specifications.ADR.md) for design
details.

### Headers

- `Authorization: <Valid Auth token>`

### Success Response

`200 OK`

#### Headers

#### Body

##### Schema

> TODO

##### Content (example)

```text
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

- `<type N>` is a data type ID from the [Mappings.py](./staging_service/autodetect/Mappings.py)
  file and the Narrative staging area configuration file - it is a shared namespace
  between the staging service and Narrative to specify bulk applications, and has a
  1:1 mapping to an app. It is determined by the first header line from the templates.
- `<spec.json ID N>` is the ID of an input parameter from a `KB-SDK` app's `spec.json` file.
  These are determined by the second header line from the templates and will differ
  by the data type.
- `<value for ID, row N>` is the user-provided value for the input for a given
  `spec.json`
  ID and import or analysis instance, where an import/analysis instance is effectively a
  row in the data file. Each data file row is provided in order for each type. Each row is
  provided in a mapping of `spec.json` ID to the data for the row. Lines > 3 in the
  templates are user-provided data, and each line corresponds to a single import or analysis.
  
### Error Response

Error reponses are of the general form:

```json
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

- `cannot_find_file` if an input file cannot be found
- `cannot_parse_file` if an input file cannot be parsed
- `incorrect_column_count` if the column count is not as expected
  - For Excel files, this may mean there is a non-empty cell outside the bounds of the
    data area
- `multiple_specifications_for_data_type` if more than one tab or file per data type is submitted
- `no_files_provided` if no files were provided
- `unexpected_error` if some other error occurs

The HTTP code returned will be, in order of precedence:

- 400 if any error other than `cannot_find_file` or `unexpected_error` occurs
- 404 if at least one error is `cannot_find_file` but there are no 400-type errors
- 500 if all errors are `unexpected_error`

The per error type data structures are:

#### `cannot_find_file`

```json
{
    "type": "cannot_find_file",
    "file": <filepath>
}
```

#### `cannot_parse_file`

```json
{
    "type": "cannot_parse_file",
    "file": <filepath>,
    "tab": <spreadsheet tab if applicable, else null>,
    "message": <message regarding the parse error>
}
```

#### `incorrect_column_count`

```json
{
    "type": "incorrect_column_count",
    "file": <filepath>,
    "tab": <spreadsheet tab if applicable, else null>,
    "message": <message regarding the error>
}
```

#### `multiple_specifications_for_data_type`

```json
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

```json
{
    "type": "no_files_provided"
}
```

#### `unexpected_error`

```json
{
    "type": "unexpected_error",
    "file": <filepath if applicable to a single file>
    "message": <message regarding the error>
}
```

## Write bulk specifications

`POST /write_bulk_specification`

This endpoint is the reverse of the parse bulk specifications endpoint - it takes a similar
data structure to that which the parse endpoint returns and writes bulk specification templates.

### Headers

- `Authorization: <KBase Auth token>`
- `Content-Type: application/json`

#### Body

##### Schema

> TODO

##### Content (example)

```json
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

- `output_directory` specifies where the output files should be written in the user's
   staging area.
- `output_file_type` specifies the format of the output files.
- `<type N>` is a data type ID from the [Mappings.py](./staging_service/autodetect/Mappings.py)
  file and the Narrative staging area configuration file - it is a shared namespace
  between the staging service and Narrative to specify bulk applications, and has a
  1:1 mapping to an app. It is included in the first header line in the templates.
- `order_and_display` determines the ordering of the columns in the written templates,
  as well as mapping the spec.json ID of the parameter to the human readable name of the
  parameter in the display.yml file.
- `<spec.json ID N>` is the ID of an input parameter from a `KB-SDK` app's `spec.json` file.
  These are written to the second header line from the import templates and will differ
  by the data type.
- `data` contains any data to be written to the file as example data, and is analagous
   to the data structure returned from the parse endpoint. To specify that no data
   should be written to the template provide an empty list.
- `<value for ID, row N>` is the value for the input for a given `spec.json` ID
  and import or analysis instance, where an import/analysis instance is effectively a row
  in the data file. Each data file row is provided in order for each type. Each row is
  provided in a mapping of `spec.json` ID to the data for the row. Lines > 3 in the
  templates are user-provided data, and each line corresponds to a single import or analysis.

### Success Response

`200 OK`

#### Headers

- `Content-Type: application/json`

#### Body

##### Schema

> TODO

##### Content (example)

```json
{
    "output_file_type": <one of "CSV", "TSV", or "EXCEL">,
    "files": {
        <type 1>: <staging service path to file containg data for type 1>,
        ...
        <type N>: <staging service path to file containg data for type N>,
    }
}
```

- `output_file_type` has the same definition as above.
- `files` contains a mapping of each provided data type to the output template file for
  that type. In the case of Excel, all the file paths will be the same since the data
  types are all written to different tabs in the same file.
  
### Error Response

Method specific errors have the form:

```json
{"error": "<error message>"}
```

The error code in this case will be a 4XX error.

The AioHTTP server may also return built in errors that are not in JSON format - an
example of this is overly large (> 1MB) request bodies.

## Get Importer Mappings

`POST /importer_mappings`

This endpoint returns:

1) a mapping between a list of files and predicted importer apps, and
2) a file information list that includes the input file names split between the file
   prefix and the file suffix, if any, that was used to determine the file -> importer
   mapping, and a list of file types based on the file suffix. If a file has a suffix
   that does not match any mapping (e.g. `.sys`), the suffix will be `null`, the prefix
   the entire file name, and the file type list empty.

For example,

- if we pass in nothing we get a response with no mappings
- if we pass in a list of files, such as ["file1.fasta", "file2.fq", "None"], we would
   get back a response that maps to Fasta Importers and FastQ Importers, with a weight
   of 0 to 1 which represents the probability that this is the correct importer for you.
- for files for which there is no predicted app, the return is a null value
- this endpoint is used to power the dropdowns for the staging service window in the Narrative

### Headers

none

### Success Response

`200 OK`

#### Headers

- `Content-Type: application/json`

#### Body

##### Schema

> TODO

##### Content (example)

```python
data = {"file_list": ["file1.txt", "file2.zip", "file3.gff3.gz"]}
    async with AppClient(config, username) as cli:
        resp = await cli.post(
            "importer_mappings/", data=data
        )
```

```json
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

### Error Responses

> TODO: hopefully the typical 401/400 auth errors are returned

#### `400 Bad Request`

##### Headers

- `Content-Type: text/plain`

##### Body

```text
must provide file_list field 
```

## Get importer filetypes

`GET /importer_filetypes`

This endpoint returns information about the file types associated with data types and
the file extensions for those file types. It is primarily of use for creating UI
elements describing which file extensions may be selected when performing bulk file
selections.

### Headers

none

### Success Response

`200 OK`

#### Headers

#### Body

##### Schema

> TODO

##### Content (example)

```json
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

- `<type N>` is a data type ID from the [Mappings.py](./staging_service/autodetect/Mappings.py)
  file and the Narrative staging area configuration file - it is a shared namespace
  between the staging service and Narrative to specify bulk applications, and has a
  1:1 mapping to an import app. It is included in the first header line in the templates.
- `<file type N>` is a file type like `FASTA` or `GENBANK`. The supported file types are
  listed below.
- `<extension N>` is a file extension like `*.fa` or `*.gbk`.

## Autodetect App and File Type IDs

### App type IDs

These are the currently supported upload app type IDs:

```text
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

### File type IDs

These are the currently supported file type IDs. These are primarily useful for apps
that take two different file types, like GFF/FASTA genomes.

```text
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

## Common Authorization Error Responses

### `401 Unauthorized`

Authentication is incorrect

#### Content

`text/plain`

```text
Error Connecting to auth service ...
```

### `400 Bad Request`

Results if the `Authorization` header field is absent or empty

> TODO: this should be a 403

#### Content

`text/plain`

```text
Must supply token
```
