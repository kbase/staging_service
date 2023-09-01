#!/usr/bin/env python3
"""
Quick and dirty temporary code for generating a bulk import template. Should probably
live somewhere else long term, maybe the narrative? ... and be rewritten with tests

Doesn't do any error handling as it's expected that only KBase developers will run this code.

Currently only works on modules in the released state, but that wouldn't be hard to fix.

Currently will only work for relatively simple specs - e.g. no grouped parameters etc.
"""

import argparse
import json
import sys
from clients.narrative_method_store_client import NarrativeMethodStore

_HEADER_SEP = ";"

_NMS_URLS = {
    # including the entire url vs constructing it makes this easy to update for local NMS
    # instances or whatever
    "prod": "https://kbase.us/services/narrative_method_store/rpc",
    # prod and appdev point to the same service... *shrug*
    "appdev": "https://appdev.kbase.us/services/narrative_method_store/rpc",
    "next": "https://next.kbase.us/services/narrative_method_store/rpc",
    "ci": "https://ci.kbase.us/services/narrative_method_store/rpc",
}

_FORMAT_VERSION = 1  # evolve the format by making changes and incrementing the version


def parse_args():
    parser = argparse.ArgumentParser(
        description="Generate a bulk import template for an app"
    )
    parser.add_argument(
        "app_id",
        help="The app ID to process, for example kb_uploadmethods/import_sra_as_reads_from_staging",
    )
    parser.add_argument(
        "data_type",
        help="The datatype corresponding to the the app. This id is shared between the "
        + "staging service and the narrative, for example sra_reads",
    )
    parser.add_argument(
        "--tsv",
        action="store_true",
        help="Create a TSV file rather than a CSV file (the default)",
    )
    parser.add_argument(
        "--env",
        choices=["prod", "appdev", "next", "ci"],
        default="prod",
        help="The KBase environment to query, default prod",
    )
    parser.add_argument(
        "--print-spec",
        action="store_true",
        help="Print the input specification for the app to stderr",
    )
    return parser.parse_args()


def is_file_input(param):
    if param["field_type"] != "dynamic_dropdown":
        return False
    if "dynamic_dropdown_options" not in param:
        raise ValueError(
            "Missing dynamic_dropdown_options field for dynamic_dropdown input"
        )
    return param["dynamic_dropdown_options"].get("data_source") == "ftp_staging"


def is_object_name(param):
    return "text_options" in param and param["text_options"].get("is_output_name")


def is_advanced(param):
    return bool(param.get("advanced"))


def parameter_order(param):
    if is_file_input(param):
        return 1
    if is_object_name(param):
        return 2
    if is_advanced(param):
        return 4
    return 3


def sort_params(params):
    new_params = []
    for i, p in enumerate(params):
        p = dict(p)  # make a copy, don't change the input
        p["i"] = i
        new_params.append(p)
    return sorted(new_params, key=lambda p: (parameter_order(p), p["i"]))


def main():
    args = parse_args()
    nms = NarrativeMethodStore(_NMS_URLS[args.env])
    spec = nms.get_method_spec({"ids": [args.app_id]})
    if args.print_spec:
        print(json.dumps(spec[0]["parameters"], indent=4), file=sys.stderr)
    params = sort_params(spec[0]["parameters"])
    sep = "\t" if args.tsv else ", "
    print(
        f"Data type: {args.data_type}{_HEADER_SEP} "
        + f"Columns: {len(params)}{_HEADER_SEP} Version: {_FORMAT_VERSION}"
    )
    # we could theoretically use the parameter order to note for the users the type of each
    # column - e.g. file input, output name, params, advanced params
    # That's not in scope for now
    print(sep.join([p["id"] for p in params]))
    print(sep.join([p["ui_name"] for p in params]))


if __name__ == "__main__":
    main()
