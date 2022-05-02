### Version 1.3.4
- Alter the behavior of the bulk specification file writers to return an error if the
  input `types` parameter is empty.
- Fixed a bug in the csv/tsv bulk specification parser that would case a failure if the
  first header of a file had trailing separators. This occurs if a csv/tsv file is opened and
  saved by Excel.

### Version 1.3.3
- Fixed a bug in the csv/tsv bulk specification parser that would include an empty entry for
  each empty line in the file.

### Version 1.3.2
- Add `write_bulk_specification` endpoint for writing bulk specifications
- Add `import_filetypes` endpoint for getting datatype -> filetype -> extension mappings
- Fixed a bug in the csv/tsv bulk specification parser that would throw an error on any empty
  lines in the file, even at the end. The parser now ignores empty lines the same way the Excel
  parser does.
- Fixed a bug in the `bulk_specification` endpoint where a missing header item in a `*.?sv`
  file would cause it to be replaced with a strange name.
- Fixed a bug in the `bulk_specification` endpoint where a missing header item in an Excel
  file would cause a duplicate header error rather than a missing header error.
- As part of the two fixes above, some error message text has changed due to the rewrite of the
  parsers.

### Version 1.3.1
- added the `files` key to the returned data from the `bulk_specification` endpoint.

### Version 1.3.0
- Update to Python 3.9
- Add `bulk_specification` endpoint for parsing import specifications

### Version 1.2.0
- BACKWARDS INCOMPATIBILITY: remove the unused `apps` key from the importer mappings endpoint.
- added a `fileinfo` field to the return of the importer mappings endpoint that includes the
  file prefix, suffix, and file type(s), if any.
- reverted change to expose dotfiles in the api by default
- attempting to upload a dotfile will now cause an error

### Version 1.1.9
- Added support for Genbank *.gb and *.gbff extensions
- Added support for gzipped Reads, Assemblies, Genbank Files, and GFF files.

### Version 1.1.8
- Added new endpoint `importer-mappings/` for getting a mapping of importers for file names
- Updated endpoint to use GET and query_string
- Ran black
- BUGFIX: Change head/tail functionality to return 1024 chars to avoid bad cases with really large one line files
- Update FASTQ/SRA to use their own APP Uis

### Version 1.1.7
- Add a file name check to void user uploading files with name starting with space
- Update list endpoint so that it only hide .globus_id file by default

### Version 1.1.3
- Add a add-acl-concierge endpoint
- Added configs for that endpoint
- Added options to dockerfile/docker-compose

### Version 1.1.2
- Added capability to check 'kbase_session_backup' cookie
- Added a `add-acl` and `remove-acl` endpoint for globus endpoint access
- Change logging to STDOUT


### Version 1.1.0
- Added a `download` endpoint for files
