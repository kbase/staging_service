import asyncio
import configparser
import json
import logging
import os
import sys

import globus_sdk
from aiohttp.web import HTTPInternalServerError, HTTPOk


async def run_command(*args):
    """Run command in subprocess
    Example from:
        http://asyncio.readthedocs.io/en/latest/subprocess.html
    """
    # Create subprocess
    process = await asyncio.create_subprocess_exec(
        *args,
        # stdout must a pipe to be accessible as process.stdout
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    # Status
    # print('Started:', args, '(pid = ' + str(process.pid) + ')')

    # Wait for the subprocess to finish
    stdout, stderr = await process.communicate()

    # Progress
    if process.returncode == 0:
        return stdout.decode().strip()
    else:
        error_msg = "command {cmd} failed\nreturn code: {returncode}\nerror: {error}".format(
            cmd=" ".join(args),
            returncode=process.returncode,
            error=stderr.decode().strip(),
        )
        raise HTTPInternalServerError(text=error_msg)


class Path(object):
    _META_DIR = None  # expects to be set by config
    _DATA_DIR = None  # expects to be set by config
    _CONCIERGE_PATH = None  # expects to be set by config
    _FILE_EXTENSION_MAPPINGS = None  # expects to be set by config

    __slots__ = ["full_path", "metadata_path", "user_path", "name", "jgi_metadata"]

    def __init__(self, full_path, metadata_path, user_path, name, jgi_metadata):
        self.full_path = full_path
        self.metadata_path = metadata_path
        self.user_path = user_path
        self.name = name
        self.jgi_metadata = jgi_metadata

    @staticmethod
    def validate_path(username: str, path: str = ""):
        """
        @returns a path object based on path that must start with username
        """
        if len(path) > 0:
            path = os.path.normpath(path)
            path = path.replace("..", "/")
            path = os.path.normpath(path)
            if path == ".":
                path = ""
            while path.startswith("/"):
                path = path[1:]
        user_path = os.path.join(username, path)
        full_path = os.path.join(Path._DATA_DIR, user_path)

        metadata_path = os.path.join(Path._META_DIR, user_path)
        name = os.path.basename(path)
        jgi_metadata = os.path.join(os.path.dirname(full_path), "." + name + ".jgi")
        return Path(full_path, metadata_path, user_path, name, jgi_metadata)

    @staticmethod
    def from_full_path(full_path: str):
        user_path = full_path[len(Path._DATA_DIR) :]
        if user_path.startswith("/"):
            user_path = user_path[1:]
        metadata_path = os.path.join(Path._META_DIR, user_path)
        name = os.path.basename(full_path)
        jgi_metadata = os.path.join(os.path.dirname(full_path), "." + name + ".jgi")
        return Path(full_path, metadata_path, user_path, name, jgi_metadata)


class AclManager:
    def __init__(self):
        """
        The ACLManager is used to add and remove acl endpoints for KBase Users on our Globus Share
        """
        logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
        config = configparser.ConfigParser()
        config.read("/etc/globus.cfg")
        cf = config["globus"]
        self.endpoint_id = cf["endpoint_id"]

        client = globus_sdk.NativeAppAuthClient(cf["client_id"])
        try:
            transfer_authorizer = globus_sdk.RefreshTokenAuthorizer(
                cf["transfer_token"], client
            )
            self.globus_transfer_client = globus_sdk.TransferClient(
                authorizer=transfer_authorizer
            )
            auth_authorizer = globus_sdk.RefreshTokenAuthorizer(
                cf["auth_token"], client
            )
            self.globus_auth_client = globus_sdk.AuthClient(authorizer=auth_authorizer)
        except globus_sdk.GlobusAPIError as error:
            logging.error(str(error.code) + error.raw_text)
            raise HTTPInternalServerError(
                text=str("Invalid Token Specified in globus.cfg file")
            )

    def _get_globus_identities(self, shared_directory: str):
        """
        Parse the .globus_id file for a filename and get the first item. Then use that account name
        to call the globus service and get identities for that client.
        """
        globus_id_filename = "{}.globus_id".format(shared_directory)
        with open(globus_id_filename, "r") as fp:
            ident = fp.read()
            return self.globus_auth_client.get_identities(
                usernames=ident.split("\n")[0]
            )

    def _get_globus_identity(self, globus_id_filename: str):
        """
        Get the first identity for the username in the .globus_id file
        """
        try:
            return self._get_globus_identities(globus_id_filename)["identities"][0][
                "id"
            ]
        except FileNotFoundError as error:
            response = {
                "success": False,
                "error_type": "FileNotFoundError",
                "strerror": error.strerror,
                "filename": error.filename,
                "error_code": error.errno,
            }
            logging.error(response)

            raise HTTPInternalServerError(
                text=json.dumps(response), content_type="application/json"
            )

        except globus_sdk.GlobusAPIError as error:
            response = {
                "success": False,
                "error_type": "GlobusAPIError",
                "message": error.message,
                "code": error.code,
                "http_status": error.http_status,
            }
            logging.error(response)

            raise HTTPInternalServerError(
                text=json.dumps(response), content_type="application/json"
            )

    def _add_acl(self, user_identity_id: str, shared_directory_basename: str):
        """
        Attempt to add acl for the given user id and directory
        """
        try:
            resp = self.globus_transfer_client.add_endpoint_acl_rule(
                self.endpoint_id,
                dict(
                    DATA_TYPE="access",
                    principal=user_identity_id,
                    principal_type="identity",
                    path=shared_directory_basename,
                    permissions="rw",
                ),
            )

            response = {
                "success": True,
                "principal": user_identity_id,
                "path": shared_directory_basename,
                "permissions": "rw",
            }

            logging.info(response)
            logging.info(
                "Shared %s with %s\n" % (shared_directory_basename, user_identity_id)
            )

            logging.info(response)
            return response

        except globus_sdk.TransferAPIError as error:
            response = {
                "success": False,
                "error_type": "TransferAPIError",
                "error": error.message,
                "error_code": error.code,
                "shared_directory_basename": shared_directory_basename,
            }
            logging.error(response)
            if error.code == "Exists":
                raise HTTPOk(text=json.dumps(response), content_type="application/json")

        raise HTTPInternalServerError(
            text=json.dumps(response), content_type="application/json"
        )

    def _remove_acl(self, user_identity_id: str):
        """
        Get all ACLS and attempt to remove the correct ACL for the given user_identity
        """
        try:
            acls = self.globus_transfer_client.endpoint_acl_list(self.endpoint_id)[
                "DATA"
            ]
            for acl in acls:
                if user_identity_id == acl["principal"]:
                    if "id" in acl and acl["id"] is not None:
                        resp = self.globus_transfer_client.delete_endpoint_acl_rule(
                            self.endpoint_id, acl["id"]
                        )
                        return {"message": str(resp), "Success": True}
                    else:
                        return {
                            "message": "Couldn't find ACL for principal. Did you already delete your ACL?",
                            "Success": False,
                            "principal": acl["principal"],
                        }

            response = {
                "success": False,
                "error_type": "Could Not Find or Delete User Identity Id (ACL)",
                "user_identity_id": user_identity_id,
            }
            raise HTTPInternalServerError(
                text=json.dumps(response), content_type="application/json"
            )

        except globus_sdk.GlobusAPIError as error:
            response = {
                "success": False,
                "error_type": "GlobusAPIError",
                "user_identity_id": user_identity_id,
            }
            raise HTTPInternalServerError(
                text=json.dumps(response), content_type="application/json"
            )

    def add_acl_concierge(self, shared_directory: str, concierge_path: str):
        """
        Add ACL to the concierge globus share via the globus API
        :param shared_directory: Dir to get globus ID from and to generate id to create ACL for share
        :param shared_concierge_directory: KBase Concierge Dir to add acl for
        :return: Result of attempt to add acl
        """
        user_identity_id = self._get_globus_identity(shared_directory)
        cp_full = f"{Path._DATA_DIR}/{concierge_path}"
        try:
            os.mkdir(cp_full)
            print(f"Attempting to create concierge dir {cp_full}")
        except FileExistsError as e:
            print(e)

        return self._add_acl(user_identity_id, concierge_path)

    def add_acl(self, shared_directory: str):
        """
        Add ACL to the globus share via the globus API
        :param shared_directory: Directory to get globus ID from and to generate id to create ACL for share
        :return: Result of attempt to add acl
        """
        user_identity_id = self._get_globus_identity(shared_directory)
        base_name = "/{}/".format(shared_directory.split("/")[-2])
        return self._add_acl(user_identity_id, base_name)

    def remove_acl(self, shared_directory: str):
        """
        Remove ACL from the globus share via the globus API
        :param shared_directory: Directory to get globus ID from and to generate id to remove ACL
        :return:  Result of attempt to remove acl
        """
        user_identity_id = self._get_globus_identity(shared_directory)
        return self._remove_acl(user_identity_id)
