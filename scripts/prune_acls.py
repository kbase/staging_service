#!/root/bulk/acl_manager/py3globus/bin/python

"""
Deletes ACLS from globus, and then clears out directories older than THRESHOLD (60) days
"""
from __future__ import print_function  # for python 2

import logging
import time
import shutil
from collections import namedtuple

from os.path import getmtime

import globus_sdk
from globus_sdk import TransferAPIError
import configparser

"""
Setup clients and read token
"""
current_time = time.time()
THRESHOLD_DAYS = 60

admin_acls = [
    "9cb619d0-4417-11e8-8e06-0a6d4e044368",
    "580118b2-dc53-11e6-9d02-22000a1e3b52",
]
admin_names = ["dolsonadmin", "dolson"]

config = configparser.ConfigParser()
config.read("globus.cfg")
cf = config["globus"]
endpoint_id = cf["endpoint_id"]

client = globus_sdk.NativeAppAuthClient(cf["client_id"])
try:
    transfer_authorizer = globus_sdk.RefreshTokenAuthorizer(
        cf["transfer_token"], client
    )
    globus_transfer_client = globus_sdk.TransferClient(authorizer=transfer_authorizer)
    auth_authorizer = globus_sdk.RefreshTokenAuthorizer(cf["auth_token"], client)
    globus_auth_client = globus_sdk.AuthClient(authorizer=auth_authorizer)
except globus_sdk.GlobusAPIError as error:
    logging.error(str(error.code) + error.raw_text)
    raise Exception(str("Invalid Token Specified in globus.cfg file"))


def remove_directory(directory):
    """
    :param directory: Directory to DELETE
    :return: Log success or failure of deleting this directory to the log
    """
    try:
        logging.info("About to delete {}".format(directory))
        # shutil.rmtree(directory)
    except OSError as error:
        logging.error(
            "Couldn't delete {} {} {}".format(directory, error.message, error.filename)
        )


def remove_acl(acl):
    """
    :param acl: ACL To Delete
    :return: Logs success or failure of deleting this ACL to the log
    """
    logging.info(
        "{}:About to remove ACL {} for {} (> {} days)".format(
            current_time, acl["id"], acl["path"], THRESHOLD_DAYS
        )
    )
    try:
        resp = globus_transfer_client.delete_endpoint_acl_rule(endpoint_id, acl["id"])
    except TransferAPIError as error:
        logging.error(error.raw_text)


def main():
    logging.basicConfig(filename="prune_acl.log", level=logging.INFO)
    logging.info("{}:BEGIN RUN".format(current_time))

    old_acls = get_old_acls()

    logging.info(
        "{}:ATTEMPTING TO DELETE {} OLD ACLS".format(current_time, len(old_acls))
    )
    for acl in old_acls:
        remove_acl(acl.acl)
        remove_directory(acl.dir)
    logging.info("{}:END RUN".format(current_time))


def get_endpoint_acls():
    """
    :return: Return a dictionary of endpoint ACLS using the Globus API
    """
    try:
        return globus_transfer_client.endpoint_acl_list(endpoint_id)["DATA"]
    except TransferAPIError as error:
        print(error)


def directory_is_old(directory):
    """
    :param directory:
    :return: True or False depending on whether the directory has not been modified in more than THRESHOLD days
    """
    try:
        age = current_time - getmtime(directory)
    except OSError:
        return False

    days = age / 60 / 60 / 24
    if days > THRESHOLD_DAYS:
        return True
    return False


def get_old_acls():
    """
    Get the size and modified date of the directories for each ACL
    If the directory > threshold days, add it to the list of old_acls to be removed
    :return: A list of ACLs to be removed
    """
    acls = get_endpoint_acls()
    logging.info("{}:FOUND {} acls".format(current_time, len(acls)))
    old_acls = []
    old_acl_and_dir = namedtuple("old_acl_and_dir", "acl dir")
    for acl in acls:
        directory = "/dtn/disk0/bulk" + acl["path"]
        if directory_is_old(directory) and acl["id"] not in admin_acls:
            oad = old_acl_and_dir(acl, directory)
            old_acls.append(oad)

    return old_acls


if __name__ == "__main__":
    main()
