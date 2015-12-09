#!/usr/bin/env python3

import re
import sys
import time
from collections import defaultdict


def parse(line):
    # data = re.match("I, \[(?P<date>.*) #(?P<id>.*)\]  (?P<level>.*) -- : Started (?P<method>.*) \"(?P<resource>.*)\" for (?P<client>.*) at (?P<datetime>.*)", line)
    data = re.match("Started (?P<method>.*) \"(?P<resource>.*)\" for (?P<client>.*) at (?P<datetime>.*)", line)
    if data is None:
        return
    return data.groupdict()


class Log(dict):
    KEY = 'client'

    def parse_caseflow_url(self):
        url = self['resource']
        if not url.startswith("/caseflow/certifications/"):
            return (None, url)

        chunks = url.split("/", 5)
        if len(chunks) < 5:
            return (None, url)

        page = chunks[-1].split("?", 1)[0]
        return chunks[-2], page


class Record(list):
    def flow(self):
        return (x[1] for x in (y.parse_caseflow_url() for y in self) if x[0] is not None)

    def start(self):
        return 'start' in self.flow()

    def certified(self):
        return 'certify' in self.flow()

    def aborted(self):
        return 'error' in self.flow()

    def question(self):
        return 'questions' in self.flow()

    def generated(self):
        return 'generate' in self.flow()

    FLOW = (
        (start, "S"),
        (question, "Q"),
        (generated, "G"),
        (certified, "C"),
        (aborted, "A"),
    )

    def status(self):
        return "".join((char for (func, char) in self.FLOW if func(self)))


class Report(dict):
    pass


class Logs(object):
    def __init__(self):
        self.activity = defaultdict(list)

    def log(self, data):
        if data is None:
            return

        if not data['resource'].startswith("/caseflow/certifications/"):
            return

        entry = Log(data)
        bfkey, _ = entry.parse_caseflow_url()
        self.activity[bfkey].append(entry)

    def tailer(self, path):
        with open(path, 'r') as fd:
            for el in fd:
                yield (el, True)
            yield ("", False)
            while True:
                seen = False
                for line in fd:
                    seen = True
                    yield (line, False)
                if not seen:
                    time.sleep(0.05)

    def report(self):
        return Report({k: Record(v) for (k, v) in self.activity.items()})

    def tail(self, path):
        for el, bulk in self.tailer(path):
            self.log(parse(el))
            if not bulk:
                yield self.report()


def print_flow(flow, length=5):
    if len(flow) >= length:
        flow = ["..."] + flow[:length]
    print("   " + " -> ".join(flow))


def main(path):
    logs = Logs()
    for report in logs.tail(path):
        print("[2J[1;1HStatus of Cases:\n")
        for (key, record) in report.items():
            sys.stdout.write("{}".format(key))
            if record.question():
                sys.stdout.write("[33m")
            if record.generated():
                sys.stdout.write("[34m")
            if record.aborted():
                sys.stdout.write("[31m[1m")
            if record.certified():
                sys.stdout.write("[32m")
            sys.stdout.write("[30G" + record.status() + "[0m\n")
        sys.stdout.flush()


if __name__ == "__main__":
    main(*sys.argv[1:])
