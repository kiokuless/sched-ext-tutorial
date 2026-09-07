#!/usr/bin/env python3
# SPDX-License-Identifier: MIT OR Apache-2.0
"""Print the current time and the interval between samples after each sleep(1)."""

import argparse
from datetime import datetime
import os
import time

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--sched-ext", action="store_true", help="use the loaded sched_ext scheduler")
args = parser.parse_args()

if args.sched_ext:
    # Linux's SCHED_EXT policy is 7. Change this thread's scheduling policy.
    os.sched_setscheduler(0, 7, os.sched_param(0))

previous = None
sample = 1
try:
    while True:
        now = time.monotonic()
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        interval = "" if previous is None else f"  (+{now - previous:.3f} s)"
        print(f"[{timestamp}] sample{sample}{interval}", flush=True)
        previous = now
        sample += 1
        time.sleep(1)
except KeyboardInterrupt:
    pass
