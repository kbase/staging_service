# staging_service

setup local development

must have docker installed

if you want to run it locally you must have python3.6 installed


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

to run tests TODO

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

## Get Importer Mappings

This endpoint returns:
1) a mapping between a list of files and predicted importer apps, and
2) the input file names split between the file prefix and the the file suffix, if any, that was
   used to determine the file -> importer mapping. If a file has a suffix that does not match
   any mapping (e.g. `.sys`), the suffix will be `null` and the prefix the entire file name.

For example,
 * if we pass in nothing we get a response with no mappings
 * if we pass in a list of files, such as ["file1.fasta", "file2.fq", "None"], we would get back a response
 that maps to Fasta Importers and FastQ Importers, with a weight of 0 to 1 
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
            "file_type": "CompressedFileFormatArchive",
        }],
        [{
            'app_weight': 1,
            'id': 'gff_genome',
            'title': 'GFF/FASTA Genome',
            'file_type': ['GFF']
          },
         {
            'app_weight': 1,
            'id': 'gff_metagenome',
            'title': 'GFF/FASTA MetaGenome',
            'file_type': ['GFF']
        }]
    ],
    "fileinfo": [
        {"prefix": "file1.txt", "suffix": null},
        {"prefix": "file2", "suffix": "zip"},
        {"prefix": "file3", "suffix": "gff3.gz"}
    ]
}
```
### Error Response
**Code** : `400 Bad Request`

**Content**
```
must provide file_list field 
```

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