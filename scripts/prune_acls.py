#!/root/bulk/acl_manager/py3globus/bin/python

"""
Simulates deleting ACLS from Globus and clearing out directories older than THRESHOLD (60) days without actually performing the deletions.
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

# Dry-run mode
DRY_RUN = True  # Set to False to perform actual deletions

current_time = time.time()
THRESHOLD_DAYS = 60

admin_acls = ['9cb619d0-4417-11e8-8e06-0a6d4e044368', '580118b2-dc53-11e6-9d02-22000a1e3b52']
admin_names = ['dolsonadmin', 'dolson']

config = configparser.ConfigParser()
config.read("globus.cfg")
cf = config['globus']
endpoint_id = cf['endpoint_id']

client = globus_sdk.NativeAppAuthClient(cf['client_id'])
try:
    transfer_authorizer = globus_sdk.RefreshTokenAuthorizer(cf['transfer_token'], client)
    globus_transfer_client = globus_sdk.TransferClient(authorizer=transfer_authorizer)
    auth_authorizer = globus_sdk.RefreshTokenAuthorizer(cf['auth_token'], client)
    globus_auth_client = globus_sdk.AuthClient(authorizer=auth_authorizer)
except globus_sdk.GlobusAPIError as error:
    logging.error(str(error.code) + error.raw_text)
    raise Exception("Invalid Token Specified in globus.cfg file")


def remove_directory(directory):
    """
    Logs what would be deleted instead of actually deleting it in dry-run mode.
    """
    if DRY_RUN:
        logging.info(f"[DRY-RUN] Would delete: {directory}")
    else:
        try:
            logging.info(f"Deleting {directory}")
            shutil.rmtree(directory)
        except OSError as error:
            logging.error(f"Couldn't delete {directory}: {error}")


def remove_acl(acl):
    """
    Logs what would be removed instead of actually removing it in dry-run mode.
    """
    logging.info(f"{current_time}:About to remove ACL {acl['id']} for {acl['path']} (> {THRESHOLD_DAYS} days)")
    
    if DRY_RUN:
        logging.info(f"[DRY-RUN] Would remove ACL {acl['id']} for {acl['path']}")
    else:
        try:
            globus_transfer_client.delete_endpoint_acl_rule(endpoint_id, acl['id'])
        except TransferAPIError as error:
            logging.error(error.raw_text)


def main():
    logging.basicConfig(filename='prune_acl.log', level=logging.INFO)
    logging.info(f"{current_time}:BEGIN RUN (DRY_RUN={DRY_RUN})")

    old_acls = get_old_acls()

    logging.info(f"{current_time}:ATTEMPTING TO DELETE {len(old_acls)} OLD ACLS")
    for acl in old_acls:
        remove_acl(acl.acl)
        remove_directory(acl.dir)

    logging.info(f"{current_time}:END RUN")


def get_endpoint_acls():
    """
    Returns a dictionary of endpoint ACLs using the Globus API.
    """
    try:
        return globus_transfer_client.endpoint_acl_list(endpoint_id)['DATA']
    except TransferAPIError as error:
        logging.error(error)
        return []


def directory_is_old(directory):
    """
    Checks if the directory has not been modified in more than THRESHOLD days.
    """
    try:
        age = current_time - getmtime(directory)
        days = age / (60 * 60 * 24)
        return days > THRESHOLD_DAYS
    except OSError:
        return False


def get_old_acls():
    """
    Finds ACLs associated with directories older than the threshold.
    """
    acls = get_endpoint_acls()
    logging.info(f"{current_time}:FOUND {len(acls)} ACLs")
    old_acls = []
    old_acl_and_dir = namedtuple("old_acl_and_dir", "acl dir")

    for acl in acls:
        directory = f"/dtn/disk0/bulk{acl['path']}"
        if directory_is_old(directory) and acl['id'] not in admin_acls:
            old_acls.append(old_acl_and_dir(acl, directory))

    return old_acls


if __name__ == '__main__':
    main()
