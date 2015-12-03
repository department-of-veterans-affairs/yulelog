#!/usr/bin/env python

import sys
import sys
import json
import datetime as dt
from collections import defaultdict


def load(input_file):
    with open(input_file, 'r') as fd:
        data = json.load(fd)
    for line in data:
        line['datetime'] = dt.datetime.strptime(line['datetime'], '%Y-%m-%d %H:%M:%S -0600')
        yield line

def structured(lines):
    data = defaultdict(list)
    for line in lines:
        data[line['id']].append(line)
    return data


def parse_caseflow_url(url):
    if not url.startswith("/caseflow/certifications/"):
        return (None, url)

    chunks = url.split("/", 5)
    if chunks < 6:
        return (None, url)

    page = chunks[-1].split("?", 1)[0]
    return chunks[-2], page


def reduce(activities):
    data = defaultdict(list)
    els = (parse_caseflow_url(x['resource']) for x in activities)
    for id, action in els:
        if id is None:
            continue
        data[id].append(action)
    return data


def was_certified(flow):
    return 'certify' in flow


def main(input_file, verbose="FALse"):
    verbose = verbose.lower() == "true"

    lines = structured(sorted(load(input_file), key=lambda x: x['datetime']))
    for session, activities in lines.items():
        print("Session: {}".format(session))
        activity = reduce(activities)
        for id, flow in activity.items():
            certified = was_certified(flow)
            if certified:
                sys.stdout.write("[32m")
            else:
                sys.stdout.write("[31m")

            sys.stdout.write("  {}".format(id))
            print("[0m")
            if verbose:
                for page in flow:
                    print("    {}".format(page))


if __name__ == "__main__":
    main(*sys.argv[1:])
