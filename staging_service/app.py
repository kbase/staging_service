import json
import logging
import os
import shutil
import sys
from collections import defaultdict
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlencode, urlunparse

import aiofiles
import aiohttp_cors
from aiohttp import MultipartReader, web

from staging_service.config import (
    UPLOAD_SAVE_STRATEGY_SAVE_TO_DESTINATION,
    UPLOAD_SAVE_STRATEGY_TEMP_THEN_COPY,
    get_config,
    get_max_content_length,
    get_max_file_size,
    get_read_chunk_size,
    get_save_strategy,
)

from .app_error_formatter import format_import_spec_errors
from .autodetect.Mappings import CSV, EXCEL, TSV
from .AutoDetectUtils import AutoDetectUtils
from .globus import assert_globusid_exists, is_globusid
from .import_specifications.file_parser import (
    ErrorType,
    FileTypeResolution,
    parse_import_specifications,
)
from .import_specifications.file_writers import (
    ImportSpecWriteException,
    write_csv,
    write_excel,
    write_tsv,
)
from .import_specifications.individual_parsers import parse_csv, parse_excel, parse_tsv
from .JGIMetadata import read_metadata_for
from .metadata import add_upa, dir_info, similar, some_metadata
from .utils import AclManager, StagingPath, auth_client, run_command

logging.basicConfig(stream=sys.stdout, level=logging.WARNING)
routes = web.RouteTableDef()
VERSION = "1.3.6"

_DATATYPE_MAPPINGS = None

_APP_JSON = "application/json"

_IMPSPEC_FILE_TO_PARSER = {
    CSV: parse_csv,
    TSV: parse_tsv,
    EXCEL: parse_excel,
}

_IMPSPEC_FILE_TO_WRITER = {
    CSV: write_csv,
    TSV: write_tsv,
    EXCEL: write_excel,
}


@routes.get("/importer_filetypes/")
async def importer_filetypes(_: web.Request) -> web.json_response:
    """
    Returns the file types for the configured datatypes. The returned JSON contains two keys:

    * datatype_to_filetype, which maps import datatypes (like gff_genome) to their accepted
      filetypes (like [FASTA, GFF])

    * filetype_to_extensions, which maps file types (e.g. FASTA) to their extensions (e.g.
      *.fa, *.fasta, *.fa.gz, etc.)

    This information is currently static over the life of the server.
    """
    return web.json_response(data=_DATATYPE_MAPPINGS)


@routes.get("/importer_mappings/{query:.*}")
async def importer_mappings(request: web.Request) -> web.json_response:
    """
    Return a dictionary with two lists: apps and mappings
    Apps are a list of importers
    Mappings are a list of mapping between passed in files, and available apps
    :param request: contains a list of files e.g. ['file1.txt','file2.fasta']
    """

    file_list = parse_qs(request.query_string).get("file_list", [])
    if len(file_list) == 0:
        raise web.HTTPBadRequest(
            text=f"must provide file_list field. Your provided qs: {request.query_string}",
        )

    mappings = AutoDetectUtils.get_mappings(file_list)
    return web.json_response(data=mappings)


def _file_type_resolver(path: Path) -> FileTypeResolution:
    fi = AutoDetectUtils.get_mappings([str(path)])["fileinfo"][0]
    # Here we assume that the first entry in the file_ext_type field is the entry
    # we want. Presumably secondary entries are less general.
    ftype = fi["file_ext_type"][0] if fi["file_ext_type"] else None
    if ftype in _IMPSPEC_FILE_TO_PARSER:
        return FileTypeResolution(parser=_IMPSPEC_FILE_TO_PARSER[ftype])
    else:
        if fi["suffix"]:
            ext = fi["suffix"]
        elif path.suffix:
            ext = path.suffix[1:]
        else:
            ext = path.name
        return FileTypeResolution(unsupported_type=ext)


@routes.get("/bulk_specification/{query:.*}")
async def bulk_specification(request: web.Request) -> web.json_response:
    """
    Takes a `files` query parameter with a list of comma separated import specification file paths.
    Returns the contents of those files parsed into a list of dictionaries, mapped from the data
    type, in the `types` key.

    :param request: contains a comma separated list of files, e.g. folder1/file1.txt,file2.txt
    """
    username = await authorize_request(request)
    files = parse_qs(request.query_string).get("files", [])
    files = files[0].split(",") if files else []
    files = [f.strip() for f in files if f.strip()]
    paths = {}
    for f in files:
        p = StagingPath.validate_path(username, f)
        paths[Path(p.full_path)] = Path(p.user_path)
    # list(dict) returns a list of the dict keys in insertion order (py3.7+)
    res = parse_import_specifications(
        tuple(list(paths)),
        _file_type_resolver,
        lambda e: logging.error(
            "Unexpected error while parsing import specs", exc_info=e
        ),
    )
    if res.results:
        types = {dt: result.result for dt, result in res.results.items()}
        files = {
            dt: {"file": str(paths[result.source.file]), "tab": result.source.tab}
            for dt, result in res.results.items()
        }
        return web.json_response({"types": types, "files": files})
    errtypes = {e.error for e in res.errors}
    errtext = json.dumps({"errors": format_import_spec_errors(res.errors, paths)})
    if errtypes - {ErrorType.OTHER, ErrorType.FILE_NOT_FOUND}:
        return web.HTTPBadRequest(text=errtext, content_type=_APP_JSON)
    if errtypes - {ErrorType.OTHER}:
        return web.HTTPNotFound(text=errtext, content_type=_APP_JSON)
    # I don't think there's a good way to test this codepath
    return web.HTTPInternalServerError(text=errtext, content_type=_APP_JSON)


@routes.post("/write_bulk_specification/")
async def write_bulk_specification(request: web.Request) -> web.json_response:
    """
    Write a bulk specification template to the user's staging area.

    :param request: Expectes a JSON body as a mapping with the following keys:
        output_directory - the location where the templates should be written.
        output_file_type - one of CSV, TSV, or EXCEL. Specifies the template format.
        types - specifies the contents of the templates. This is a dictionary of data types as
            strings to the specifications for the data type. Each specification has two required
            keys:
            * `order_and_display`: this is a list of lists. Each inner list has two elements:
                * The parameter ID of a parameter. This is typically the `id` field from the
                    KBase app `spec.json` file.
                * The display name of the parameter. This is typically the `ui-name` field from the
                    KBase app `display.yaml` file.
                The order of the inner lists in the outer list defines the order of the columns
                in the resulting import specification files.
            * `data`: this is a list of str->str or number dicts. The keys of the dicts are the
                parameter IDs as described above, while the values are the values of the
                parameters. Each dict must have exactly the same keys as the `order_and_display`
                structure. Each entry in the list corresponds to a row in the resulting import
                specification, and the order of the list defines the order of the rows.
            Leave the `data` list empty to write an empty template.

    :returns: A JSON mapping with the output_file_type key identical to the above, and a mapping
        of the data types in the input "types" field to the file created for that type.
    """
    username = await authorize_request(request)
    if request.content_type != _APP_JSON:
        # There should be a way to get aiohttp to handle this but I can't find it
        return _createJSONErrorResponse(
            f"Required content-type is {_APP_JSON}",
            error_class=web.HTTPUnsupportedMediaType,
        )
    if not request.content_length:
        return _createJSONErrorResponse(
            "The content-length header is required and must be > 0",
            error_class=web.HTTPLengthRequired,
        )
    # No need to check the max content length; the server already does that. See tests
    data = await request.json()
    if type(data) != dict:
        return _createJSONErrorResponse("The top level JSON element must be a mapping")
    folder = data.get("output_directory")
    type_ = data.get("output_file_type")
    if type(folder) != str:
        return _createJSONErrorResponse(
            "output_directory is required and must be a string"
        )
    writer = _IMPSPEC_FILE_TO_WRITER.get(type_)
    if not writer:
        return _createJSONErrorResponse(f"Invalid output_file_type: {type_}")
    folder = StagingPath.validate_path(username, folder)
    os.makedirs(folder.full_path, exist_ok=True)
    try:
        files = writer(Path(folder.full_path), data.get("types"))
    except ImportSpecWriteException as e:
        return _createJSONErrorResponse(e.args[0])
    new_files = {ty: str(Path(folder.user_path) / files[ty]) for ty in files}
    return web.json_response({"output_file_type": type_, "files_created": new_files})


def _createJSONErrorResponse(error_text: str, error_class=web.HTTPBadRequest):
    err = json.dumps({"error": error_text})
    return error_class(text=err, content_type=_APP_JSON)


@routes.get("/add-acl-concierge")
async def add_acl_concierge(request: web.Request):
    username = await authorize_request(request)
    user_dir = StagingPath.validate_path(username).full_path
    concierge_path = f"{StagingPath._CONCIERGE_PATH}/{username}/"
    aclm = AclManager()
    result = aclm.add_acl_concierge(
        shared_directory=user_dir, concierge_path=concierge_path
    )
    result[
        "msg"
    ] = f"Requesting Globus Perms for the following globus dir: {concierge_path}"

    params = {"destination_id": aclm.endpoint_id, "destination_path": concierge_path}

    result["link"] = urlunparse(
        ("https", "app.globus.org", "/file-manager", None, urlencode(params), None)
    )

    return web.json_response(result)


@routes.get("/add-acl")
async def add_acl(request: web.Request):
    username = await authorize_request(request)
    user_dir = StagingPath.validate_path(username).full_path
    result = AclManager().add_acl(user_dir)
    return web.json_response(result)


@routes.get("/remove-acl")
async def remove_acl(request: web.Request):
    username = await authorize_request(request)
    user_dir = StagingPath.validate_path(username).full_path
    result = AclManager().remove_acl(user_dir)
    return web.json_response(result)


@routes.get("/test-service")
async def test_service(request: web.Request):
    return web.Response(text="staging service version: {}".format(VERSION))


@routes.get("/test-auth")
async def test_auth(request: web.Request):
    username = await authorize_request(request)
    return web.Response(text="I'm authenticated as {}".format(username))


@routes.get("/file-lifetime")
async def file_lifetime(parameter_list):
    return web.Response(text=os.environ["FILE_LIFETIME"])


@routes.get("/existence/{query:.*}")
async def file_exists(request: web.Request):
    username = await authorize_request(request)
    query = request.match_info["query"]
    user_dir = StagingPath.validate_path(username)
    try:
        show_hidden = request.query["showHidden"]
        if "true" == show_hidden or "True" == show_hidden:
            show_hidden = True
        else:
            show_hidden = False
    except KeyError:
        show_hidden = False
    # this scans the entire directory recursively just to see if one file exists... why?
    results = await dir_info(user_dir, show_hidden, query)
    filtered_results = [result for result in results if result["name"] == query]
    if filtered_results:
        exists = True
        is_folder = [file_json["isFolder"] for file_json in filtered_results]
        isFolder = all(is_folder)
    else:
        exists = False
        isFolder = False
    return web.json_response({"exists": exists, "isFolder": isFolder})


@routes.get("/list/{path:.*}")
@routes.get("/list")
async def list_files(request: web.Request):
    """
    lists the contents of a directory and some details about them
    """
    username = await authorize_request(request)

    path = StagingPath.validate_path(username, request.match_info.get("path", ""))

    if not os.path.exists(path.full_path):
        raise web.HTTPNotFound(
            text="path {path} does not exist".format(path=path.user_path)
        )
    elif os.path.isfile(path.full_path):
        raise web.HTTPBadRequest(
            text="{path} is a file not a directory".format(path=path.full_path)
        )

    show_hidden = request.query.get("showHidden", "false").lower() == "true"

    data = await dir_info(path, show_hidden, recurse=True)

    return web.json_response(data)


@routes.get("/download/{path:.*}")
async def download_files(request: web.Request):
    """
    download a file
    """
    username = await authorize_request(request)
    path = StagingPath.validate_path(username, request.match_info.get("path", ""))
    if not os.path.exists(path.full_path):
        raise web.HTTPNotFound(
            text="path {path} does not exist".format(path=path.user_path)
        )
    elif not os.path.isfile(path.full_path):
        raise web.HTTPBadRequest(
            text="{path} is a directory not a file".format(path=path.full_path)
        )
    # hard coding the mime type to force download
    return web.FileResponse(
        path.full_path, headers={"content-type": "application/octet-stream"}
    )


@routes.get("/similar/{path:.+}")
async def get_similar_files(request: web.Request):
    """
    lists similar file path for given file
    """
    username = await authorize_request(request)
    path = StagingPath.validate_path(username, request.match_info["path"])
    if not os.path.exists(path.full_path):
        raise web.HTTPNotFound(
            text="path {path} does not exist".format(path=path.user_path)
        )
    elif os.path.isdir(path.full_path):
        raise web.HTTPBadRequest(
            text="{path} is a directory not a file".format(path=path.full_path)
        )

    root = StagingPath.validate_path(username, "")
    files = await dir_info(root, show_hidden=False, recurse=True)

    similar_files = list()
    similarity_cut_off = 0.75  # adjust this cut off if necessary
    for file in files:
        if (not file.get("isFolder")) and (path.user_path != file.get("path")):
            similar_match = await similar(
                os.path.basename(path.user_path), file.get("name"), similarity_cut_off
            )
            if similar_match:
                similar_files.append(file)

    return web.json_response(similar_files)


@routes.get("/search/{query:.*}")
async def search(request: web.Request):
    """
    returns all files and folders matching the search query ordered by modified date
    """
    username = await authorize_request(request)
    query = request.match_info["query"]
    user_dir = StagingPath.validate_path(username)
    try:
        show_hidden = request.query["showHidden"]
        if "true" == show_hidden or "True" == show_hidden:
            show_hidden = True
        else:
            show_hidden = False
    except KeyError:
        show_hidden = False
    results = await dir_info(user_dir, show_hidden, query)
    results.sort(key=lambda x: x["mtime"], reverse=True)
    return web.json_response(results)


@routes.get("/metadata/{path:.*}")
async def get_metadata(request: web.Request):
    """
    creates a metadate file for the file requested and returns its json contents
    if it's a folder it returns stat data about the folder
    """
    username = await authorize_request(request)
    path = StagingPath.validate_path(username, request.match_info["path"])
    if not os.path.exists(path.full_path):
        raise web.HTTPNotFound(
            text="path {path} does not exist".format(path=path.user_path)
        )
    return web.json_response(await some_metadata(path))


@routes.get("/jgi-metadata/{path:.*}")
async def get_jgi_metadata(request: web.Request):
    """
    returns jgi metadata if associated with a file
    """
    username = await authorize_request(request)
    path = StagingPath.validate_path(username, request.match_info["path"])
    return web.json_response(await read_metadata_for(path))


def _validate_filename(filename: str):
    """
    Ensure that a given filename is acceptable for usage in the staging area.

    Raises http-response appropriate errors if the filename is invalid.
    """

    if filename.lstrip() != filename:
        raise web.HTTPForbidden(  # forbidden isn't really the right code, should be 400
            text="cannot upload file with name beginning with space"
        )

    if "," in filename:
        raise web.HTTPForbidden(  # for consistency, we use 403 again
            text="cannot upload file with ',' in name"
        )

    # may want to make this configurable if we ever decide to add a hidden files toggle to
    # the staging area UI
    if filename.startswith("."):
        raise web.HTTPForbidden(  # for consistency, we use 403 again
            text="cannot upload file with name beginning with '.'"
        )


async def _handle_upload_save_to_destination(
    stream: MultipartReader,
    destination_path: StagingPath,
    chunk_size: int,
    max_file_size: int,
):
    async with aiofiles.tempfile.NamedTemporaryFile(
        "wb",
        delete=False,
        dir=os.path.dirname(destination_path.full_path),
        prefix=".upload.",
    ) as output_file:
        temp_file_name = output_file.name
        actual_size = 0
        while True:
            if actual_size > max_file_size:
                raise web.HTTPBadRequest(
                    text=(
                        f"file size reached {actual_size:,} bytes which exceeds "
                        + f"the maximum allowed of {max_file_size:,} bytes)"
                    )
                )

            # A chunk size of 1MB seems to be a bit faster than the default of 8Kb.
            chunk = await stream.read_chunk(size=chunk_size)

            # Chunk is always a "bytes" object, but will be empty if there is nothing else
            # to read, which is considered Falsy.
            if not chunk:
                break

            actual_size += len(chunk)

            await output_file.write(
                chunk,
            )

        shutil.move(temp_file_name, destination_path.full_path)


async def _handle_upload_save_to_temp(
    stream: MultipartReader,
    destination_path: StagingPath,
    chunk_size: int,
    max_file_size: int,
):
    async with aiofiles.tempfile.NamedTemporaryFile("wb", delete=True) as output_file:
        actual_size = 0
        while True:
            if actual_size > max_file_size:
                raise web.HTTPBadRequest(
                    text=(
                        f"file size  reached {actual_size} bytes which exceeds "
                        + f"the maximum allowed of {max_file_size} bytes"
                    )
                )

            chunk = await stream.read_chunk(size=chunk_size)

            # Chunk is always a "bytes" object, but will be empty if there is nothing else
            # to read, which is considered Falsy.
            if not chunk:
                break

            actual_size += len(chunk)

            await output_file.write(chunk)

        async with aiofiles.tempfile.NamedTemporaryFile(
            "rb",
            delete=False,
            dir=os.path.dirname(destination_path.full_path),
            prefix=".upload.",
        ) as copied_file:
            shutil.copyfile(output_file.name, copied_file.name)

            shutil.move(copied_file.name, destination_path.full_path)


async def _handle_upload_save(stream: MultipartReader, destination_path: StagingPath):
    """
    Handles the file upload stream from the /upload endpoint, saving the stream, ultimately,
    to the given destination path.

    It honors a "save strategy", which is one of a set of defined methods for handling the upload.
    See the function get_save_strategy() for details.

    It also honors the "chunk size", which is used for reading up to the chunk size from the stream
    before saving. This constrains memory commitment, especially important for handling large
    files and concurrent file upload.
    """
    chunk_size = get_read_chunk_size()
    max_file_size = get_max_file_size()
    save_strategy = get_save_strategy()
    if save_strategy == UPLOAD_SAVE_STRATEGY_TEMP_THEN_COPY:
        await _handle_upload_save_to_temp(
            stream, destination_path, chunk_size, max_file_size
        )
    elif save_strategy == UPLOAD_SAVE_STRATEGY_SAVE_TO_DESTINATION:
        await _handle_upload_save_to_destination(
            stream, destination_path, chunk_size, max_file_size
        )


@routes.post("/upload")
async def upload_files_chunked(request: web.Request):
    """
    Uploads a file into the staging area.

    Ensures the current auth token is valid, and if so, returns the associated username.
    If not, will raise an exception

    Also, ensures that if there is a Globus account id available in the user's staging
    directory, it is valid.
    """

    username = await authorize_request(request)

    if not request.can_read_body:
        raise web.HTTPBadRequest(
            text="must provide destPath and uploads in body",
        )

    if request.content_length is None:
        raise web.HTTPBadRequest(text="request must include a 'Content-Length' header")

    max_content_length = get_max_content_length()
    if request.content_length > max_content_length:
        raise web.HTTPBadRequest(
            text=f"overall content length exceeds the maximum allowable of {max_content_length:,} bytes"
        )

    reader = await request.multipart()

    dest_path_part = await reader.next()

    #
    # Get the destination path, which is actually the subdirectory in which the
    # file should be placed within the user's staging directory.
    # This field must be first, because the file must come last, in order to
    # read the file stream.
    #
    if dest_path_part.name != "destPath":
        raise web.HTTPBadRequest(text="must provide destPath in body")

    destination_directory = await dest_path_part.text()

    #
    # Get the upload file part. We read the header bits, the get the
    # read and save the file stream.
    #
    user_file_part = await reader.next()

    if user_file_part.name != "uploads":
        raise web.HTTPBadRequest(text="must provide uploads in body")

    filename: str = unquote(user_file_part.filename)

    _validate_filename(filename)

    destination_path = os.path.join(destination_directory, filename)
    path = StagingPath.validate_path(username, destination_path)
    os.makedirs(os.path.dirname(path.full_path), exist_ok=True)

    # NB: errors result in an error response ... but the upload will be
    # read until the end. This is just built into aiohttp web.
    # From what I've read, it is considered unstable to have a server close
    # the request stream if an error is encountered, thus aiohttp invokes the
    # "release()" method to read the stream to completion, but does nothing with
    # the results (other than read into the buffer and).
    # It would require a more sophisticated implementation to work around this.
    # E.g. an upload stream and a progress stream - they could be plain https
    # requests - which would allow the progress stream to report errors which would
    # then abort the upload stream. The upload stream could also spin upon an error,
    # to avoid the useless bandwidth and cpu usage. This would also work with fetch,
    # allowing us to ditch XHR.
    await _handle_upload_save(user_file_part, path)

    if not os.path.exists(path.full_path):
        error_msg = "We are sorry but upload was interrupted. Please try again."
        raise web.HTTPNotFound(text=error_msg)

    response = await some_metadata(
        path,
        # these are fields to include in the result - the metadata stored
        # in the file system has other fields too.
        desired_fields=["name", "path", "mtime", "size", "isFolder"],
        source="KBase upload",
    )

    return web.json_response([response])


@routes.post("/define-upa/{path:.+}")
async def define_UPA(request: web.Request):
    """
    creates an UPA as a field in the metadata file corresponding to the filepath given
    """
    username = await authorize_request(request)
    path = StagingPath.validate_path(username, request.match_info["path"])
    if not os.path.exists(path.full_path or not os.path.isfile(path.full_path)):
        # The security model here is to not care if someone wants to put in a false upa
        raise web.HTTPNotFound(text=f"no file found found on path {path.user_path}")
    if not request.can_read_body:
        raise web.HTTPBadRequest(text="must provide 'UPA' field in body")
    body = await request.post()
    try:
        UPA = body["UPA"]
    except KeyError:
        raise web.HTTPBadRequest(text="must provide 'UPA' field in body")
    await add_upa(path, UPA)
    return web.Response(
        text="successfully updated UPA {UPA} for file {path}".format(
            UPA=UPA, path=path.user_path
        )
    )


@routes.delete("/delete/{path:.+}")
async def delete(request: web.Request):
    """
    allows deletion of both directories and files
    """
    username = await authorize_request(request)
    path = StagingPath.validate_path(username, request.match_info["path"])

    # make sure directory isn't home
    if path.user_path == username:
        raise web.HTTPForbidden(text="cannot delete home directory")

    if is_globusid(path, username):
        raise web.HTTPForbidden(text="cannot delete protected file")

    if os.path.isfile(path.full_path):
        os.remove(path.full_path)
        if os.path.exists(path.metadata_path):
            os.remove(path.metadata_path)

    elif os.path.isdir(path.full_path):
        shutil.rmtree(path.full_path)
        if os.path.exists(path.metadata_path):
            shutil.rmtree(path.metadata_path)

    else:
        raise web.HTTPNotFound(
            text="could not delete {path}".format(path=path.user_path)
        )

    return web.Response(text="successfully deleted {path}".format(path=path.user_path))


@routes.patch("/mv/{path:.+}")
async def rename(request: web.Request):
    username = await authorize_request(request)
    path = StagingPath.validate_path(username, request.match_info["path"])

    # make sure directory isn't home
    if path.user_path == username:
        raise web.HTTPForbidden(text="cannot rename or move home directory")
    if is_globusid(path, username):
        raise web.HTTPForbidden(text="cannot rename or move protected file")
    if not request.can_read_body:
        raise web.HTTPBadRequest(text="must provide newPath field in body")
    body = await request.post()
    try:
        new_path = body["newPath"]
    except KeyError:
        raise web.HTTPBadRequest(text="must provide newPath field in body")
    new_path = StagingPath.validate_path(username, new_path)
    if os.path.exists(path.full_path):
        if not os.path.exists(new_path.full_path):
            shutil.move(path.full_path, new_path.full_path)
            if os.path.exists(path.metadata_path):
                shutil.move(path.metadata_path, new_path.metadata_path)
        else:
            raise web.HTTPConflict(
                text="{new_path} already exists".format(new_path=new_path.user_path)
            )
    else:
        raise web.HTTPNotFound(text="{path} not found".format(path=path.user_path))
    return web.Response(
        text="successfully moved {path} to {new_path}".format(
            path=path.user_path, new_path=new_path.user_path
        )
    )


@routes.patch("/decompress/{path:.+}")
async def decompress(request: web.Request):
    username = await authorize_request(request)
    path = StagingPath.validate_path(username, request.match_info["path"])
    # make sure the file can be decompressed
    filename, file_extension = os.path.splitext(path.full_path)
    filename, upper_file_extension = os.path.splitext(filename)
    # TODO behavior when the unzip would overwrite something, what does it do, what should it do
    # 1 if we just don't let it do this its important to provide the rename feature,
    # 2 could try again after doign an automatic rename scheme (add nubmers to end)
    # 3 just overwrite and force
    destination = os.path.dirname(path.full_path)
    if (
        upper_file_extension == ".tar" and file_extension == ".gz"
    ) or file_extension == ".tgz":
        await run_command("tar", "xzf", path.full_path, "-C", destination)
    elif upper_file_extension == ".tar" and (
        file_extension == ".bz" or file_extension == ".bz2"
    ):
        await run_command("tar", "xjf", path.full_path, "-C", destination)
    elif file_extension == ".zip" or file_extension == ".ZIP":
        await run_command("unzip", path.full_path, "-d", destination)
    elif file_extension == ".tar":
        await run_command("tar", "xf", path.full_path, "-C", destination)
    elif file_extension == ".gz":
        await run_command("gzip", "-d", path.full_path)
    elif file_extension == ".bz2" or file_extension == "bzip2":
        await run_command("bzip2", "-d", path.full_path)
    else:
        raise web.HTTPBadRequest(
            text="cannot decompress a {ext} file".format(ext=file_extension)
        )
    return web.Response(text="succesfully decompressed " + path.user_path)


async def authorize_request(request):
    """
    Authenticate a token from kbase_session in cookies or Authorization header and return the
     username
    """
    if request.headers.get("Authorization"):
        token = request.headers.get("Authorization")
    elif request.cookies.get("kbase_session"):
        token = request.cookies.get("kbase_session")
    else:
        # this is a hack for prod because kbase_session won't get shared with the kbase.us domain
        token = request.cookies.get("kbase_session_backup")
    username = await auth_client().get_user(token)
    await assert_globusid_exists(username, token)
    return username


def inject_config_dependencies(config):
    """
    # TODO this is pretty hacky dependency injection
    # potentially some type of code restructure would allow this without a bunch of globals
    # This overwrites the PATH class and the AutoDetectUtils Class
    :param config: The staging service main config
    """

    DATA_DIR = config["staging_service"]["DATA_DIR"]
    META_DIR = config["staging_service"]["META_DIR"]
    CONCIERGE_PATH = config["staging_service"]["CONCIERGE_PATH"]
    FILE_EXTENSION_MAPPINGS = config["staging_service"]["FILE_EXTENSION_MAPPINGS"]

    if DATA_DIR.startswith("."):
        DATA_DIR = os.path.normpath(os.path.join(os.getcwd(), DATA_DIR))
    if META_DIR.startswith("."):
        META_DIR = os.path.normpath(os.path.join(os.getcwd(), META_DIR))
    if CONCIERGE_PATH.startswith("."):
        CONCIERGE_PATH = os.path.normpath(os.path.join(os.getcwd(), CONCIERGE_PATH))
    if FILE_EXTENSION_MAPPINGS.startswith("."):
        FILE_EXTENSION_MAPPINGS = os.path.normpath(
            os.path.join(os.getcwd(), FILE_EXTENSION_MAPPINGS)
        )

    StagingPath._DATA_DIR = DATA_DIR
    StagingPath._META_DIR = META_DIR
    StagingPath._CONCIERGE_PATH = CONCIERGE_PATH

    if StagingPath._DATA_DIR is None:
        raise web.HTTPInternalServerError(text="DATA_DIR missing in the config file ")

    if StagingPath._META_DIR is None:
        raise web.HTTPInternalServerError(text="META_DIR missing in the config file ")

    if StagingPath._CONCIERGE_PATH is None:
        raise web.HTTPInternalServerError(
            text="CONCIERGE_PATH missing in the config file "
        )

    if FILE_EXTENSION_MAPPINGS is None:
        raise web.HTTPInternalServerError(
            text="FILE_EXTENSION_MAPPINGS missing in the config file "
        )

    with open(
        FILE_EXTENSION_MAPPINGS, encoding="utf-8"
    ) as file_extension_mappings_file:
        AutoDetectUtils.set_mappings(json.load(file_extension_mappings_file))
        datatypes = defaultdict(set)
        extensions = defaultdict(set)
        for fileext, val in AutoDetectUtils.get_extension_mappings().items():
            # if we start using the file ext type array for anything else this might need changes
            filetype = val["file_ext_type"][0]
            extensions[filetype].add(fileext)
            for m in val["mappings"]:
                datatypes[m["id"]].add(filetype)
        global _DATATYPE_MAPPINGS
        _DATATYPE_MAPPINGS = {
            "datatype_to_filetype": {k: sorted(datatypes[k]) for k in datatypes},
            "filetype_to_extensions": {k: sorted(extensions[k]) for k in extensions},
        }


def app_factory():
    """
    Creates an aiohttp web application, with routes and configuration, and returns it.

    Used by the gunicorn server to spawn new workers.
    """
    app = web.Application(middlewares=[web.normalize_path_middleware()])
    app.router.add_routes(routes)

    # TODO: IMO (eap) cors should not be configured here, as this app should
    #       never be exposed directly to the public. The proxy should control
    #       the CORS policy.
    cors = aiohttp_cors.setup(
        app,
        defaults={
            "*": aiohttp_cors.ResourceOptions(
                allow_credentials=True, expose_headers="*", allow_headers="*"
            )
        },
    )
    # Configure CORS on all routes.
    for route in list(app.router.routes()):
        cors.add(route)

    # Saves config values into various global things; see the implementation.
    config = get_config()
    inject_config_dependencies(config)

    return app
