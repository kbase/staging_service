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

### Test Service

**URL** : `ci.kbase.us/services/staging_service/test-service`

**local URL** : `localhost:3000/test-service`

**Method** : `GET`

## Success Response

**Code** : `200 OK`

**Content example**

```
This is just a test. This is only a test.
```
### Test Auth

**URL** : `ci.kbase.us/services/staging_service/test-auth`

**local URL** : `localhost:3000/test-auth`

**Method** : `GET`

**Headers** : `Authorization: <Valid Auth token>`

## Success Response

**Code** : `200 OK`

**Content example**

```
I'm authenticated as <username>
```

## Error Response

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

### File Lifetime
**URL** : `ci.kbase.us/services/staging_service/file-lifetime`
**local URL** : `localhost:3000/file-lifetime`

**Method** : `GET`

## Success Response

**Code** : `200 OK`

**Content example**
number of days a file will be held for in staging service before being deleted
this is not actually handled by the server but is expected to be performed by a cron job which shares the env variable read here

```
90
```

### List Directory
defaults to not show hidden dotfiles

**URL** : `ci.kbase.us/services/staging_service/list/{path to directory}`

**URL** : `ci.kbase.us/services/staging_service/list/{path to directory}?showHidden={True/False}`

**local URL** : `localhost:3000/list/{path to directory}`

**local URL** : `localhost:3000/list/{path to directory}?showHidden={True/False}`

**Method** : `GET`

**Headers** : `Authorization: <Valid Auth token>`

## Success Response

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
## Error Response

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

### Search files and folders
defaults to not show hidden dotfiles

**URL** : `ci.kbase.us/services/staging_service/search/{search query}`

**URL** : `ci.kbase.us/services/staging_service/search/{search query}?showHidden={True/False}`

**local URL** : `localhost:3000/search/{search query}`

**local URL** : `localhost:3000/search/?showHidden={True/False}`

**Method** : `GET`

**Headers** : `Authorization: <Valid Auth token>`

## Success Response

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
## Error Response

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

### File and Folder Metadata

**URL** : `ci.kbase.us/services/staging_service/metadata/{path to file or folder}`

**local URL** : `localhost:3000/metadata/{path to file or folder}`

**Method** : `GET`

**Headers** : `Authorization: <Valid Auth token>`

## Success Response

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
## Error Response

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

### Upload File

**URL** : `ci.kbase.us/services/staging_service/upload`

**local URL** : `localhost:3000/upload`

**Method** : `POST`

**Headers** : `Authorization: <Valid Auth token>`

**Body constraints**

first element in request body should be

destPath: {path file should end up in}

second element in request body should be multipart file data

uploads: {multipart file}

## Success Response

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
## Error Response

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

### Define/Create UPA for file which has been imported

**URL** : `ci.kbase.us/services/staging_service/define-upa/{path to imported file}`

**local URL** : `localhost:3000/define-upa/{path to imported file}`

**Method** : `POST`

**Headers** : `Authorization: <Valid Auth token>`

**Body constraints**

first element in request body should be

UPA: {the actual UPA of imported file}

## Success Response

**Code** : `200 OK`

**Content example**

```
successfully update UPA <UPA> for file <Path>
```
## Error Response

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


### Delete file or folder (will delete things contained in folder)

**URL** : `ci.kbase.us/services/staging_service/delete/{path to file or folder}`

**local URL** : `localhost:3000/delete/{path to file or folder}`

**Method** : `DELETE`

**Headers** : `Authorization: <Valid Auth token>`

## Success Response

**Code** : `200 OK`

**Content example**

```
successfully deleted UPA <Path>
```
## Error Response

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

### Move/rename a file or folder

**URL** : `ci.kbase.us/services/staging_service/mv/{path to file or folder}`

**local URL** : `localhost:3000/mv/{path to file or folder}`

**Method** : `PATCH`

**Headers** : `Authorization: <Valid Auth token>`

**Body constraints**

first element in request body should be

newPath : {the new location/name for file or folder}

## Success Response

**Code** : `200 OK`

**Content example**

```
successfully moved <path> to <newPath>
```
## Error Response

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

### Decompress various archive formats
supported archive formats are:
.zip, .ZIP, .tar.gz, .tgz, .tar.bz, .tar.bz2, .tar, .gz, .bz2, .bzip2
**URL** : `ci.kbase.us/services/staging_service/decompress/{path to archive`

**local URL** : `localhost:3000/decompress/{path to archive}`

**Method** : `PATCH`

**Headers** : `Authorization: <Valid Auth token>`

## Success Response

**Code** : `200 OK`

**Content example**

```
successfully decompressed <path to archive>
```
## Error Response

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