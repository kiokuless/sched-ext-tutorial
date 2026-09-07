#!/usr/bin/env python3
# SPDX-License-Identifier: MIT OR Apache-2.0
"""Keep the CPU busy until Ctrl+C is pressed."""

import argparse
import os

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--sched-ext", action="store_true", help="use the loaded sched_ext scheduler")
args = parser.parse_args()

if args.sched_ext:
    os.sched_setscheduler(0, 7, os.sched_param(0))

print("CPU を使い続けています。Ctrl+C で終了します。", flush=True)
try:
    while True:
        pass
except KeyboardInterrupt:
    pass
