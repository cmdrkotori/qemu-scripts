#!/usr/bin/python
from scripts import launch
import sys

if len(sys.argv) < 3:
    launch.do_launch(None, None)
else:
    launch.do_launch(sys.argv[1], sys.argv[2:])
