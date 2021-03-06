#!/usr/bin/env python3

import re
import os
import sys
import time

from collections import defaultdict
from optparse import OptionParser
import datetime as dt


def parse(line):
    data = re.match("I, \[(?P<date>.*) #(?P<id>.*)\]  (?P<level>.*) -- : Started (?P<method>.*) \"(?P<resource>.*)\" for (?P<client>.*) at (?P<datetime>.*)", line)
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
    def start_time(self):
        return sorted(self.times())[0]

    def end_time(self):
        return sorted(self.times())[-1]

    def times(self):
        for el in self:
            yield dt.datetime.strptime(el['datetime'], "%Y-%m-%d %H:%M:%S -0600")

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
        fh = os.open(path, os.O_RDONLY | os.O_NONBLOCK)
        with os.fdopen(fh, "r") as fd:
            for el in fd:
                yield (el, True)
            yield ("", False)
            while True:
                seen = False
                for line in fd:
                    seen = True
                    yield (line, False)
                if not seen:
                    time.sleep(5)
                    yield ("", False)

    def report(self):
        return Report(dict(((k, Record(v)) for (k, v) in self.activity.items())))

    def tail(self, path):
        for el, bulk in self.tailer(path):
            self.log(parse(el))
            if not bulk:
                yield self.report()


def print_flow(flow, length=5):
    if len(flow) >= length:
        flow = ["..."] + flow[:length]
    print("   " + " -> ".join(flow))


def humanize(delta):
    seconds = total_seconds(delta)
    if seconds <= 60:
        return "less than a minute"
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)
    if days >= 1:
        return "{0} day(s), {1} hour(s)".format(days, hours)
    if hours >= 1:
        return "{0} hour(s)".format(hours)
    if minutes >= 1:
        return "{0} minute(s)".format(minutes)
    return "long ago"


def total_seconds(td):
    """
    Python 2.6 is the worst.
    """
    return (td.microseconds + (td.seconds + td.days * 24 * 3600) * 10**6) / 10**6


def main(argv):
    parser = OptionParser()
    parser.add_option("--since", dest="since", help="Format YYYY-MM-DD")
    options, (path,) = parser.parse_args(argv)

    if options.since:
        since = dt.datetime.strptime(options.since, "%Y-%m-%d")
    else:
        since = None

    logs = Logs()
    for report in logs.tail(path):
        good = 0
        total = 0
        print("[2J[1;1H\n")
        for (key, record) in sorted(report.items(), key=lambda x: x[1].end_time(), reverse=True):
            if since is not None and record.end_time() < since:
                continue

            age = dt.datetime.now() - record.end_time()
            total += 1
            sys.stdout.write("{0}".format(key))
            if record.question():
                sys.stdout.write("[33m")
            if record.generated():
                sys.stdout.write("[34m")
            if record.aborted():
                sys.stdout.write("[31m[1m")
            if record.certified():
                sys.stdout.write("[32m")
                good += 1
            sys.stdout.write("[30G" + record.status() + "[0m")
            sys.stdout.write("[40G{0} ago[0m\n".format(humanize(age)))

        print("[1;1HStatus of Cases: [1m{0}/{1}[0m certified with Caseflow\n".format(
            good, total
        ))
        sys.stdout.flush()


if __name__ == "__main__":
    main(sys.argv[1:])
