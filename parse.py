#!/usr/bin/env python

import re
import sys
import json


def parse(line):
        data = re.match("I, \[(?P<date>.*) #(?P<id>.*)\]  (?P<level>.*) -- : Started (?P<method>.*) \"(?P<resource>.*)\" for (?P<client>.*) at (?P<datetime>.*)", line)
        if data is None:
                return
        return data.groupdict()

data = []
with open(sys.argv[1], 'r') as fd:
        for line in fd:
                el = parse(line)
                if el is None:
                        continue
                data.append(el)

json.dump(data, sys.stdout)
