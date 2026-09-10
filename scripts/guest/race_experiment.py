#!/usr/bin/env python3
# SPDX-License-Identifier: MIT OR Apache-2.0
"""Show two named, fixed-work processes competing for one CPU in the lab VM."""

import argparse
from contextlib import ExitStack
from dataclasses import dataclass
import mmap
import os
from pathlib import Path
import signal
import struct
import subprocess
import sys
import tempfile
import time

from dsq_experiment import STATE, WORKLOAD, check_other_tasks, stop_process


@dataclass
class Sample:
    time: float
    done: tuple
    started: tuple
    finished: tuple


def read_sample(maps):
    # Each worker publishes four aligned native-endian u64 values. Counter reads
    # are observations, not synchronization: start/finish boundaries are omitted
    # from the rate windows below, and no sub-slice ordering is inferred.
    fields = [struct.unpack_from("=QQQQ", page) for page in maps]
    return Sample(time.monotonic(), tuple(f[0] for f in fields),
                  tuple(f[1] / 1e9 for f in fields), tuple(f[2] / 1e9 for f in fields))


def rates(samples):
    if len(samples) < 2 or samples[-1].time - samples[0].time < 1:
        return None
    elapsed = samples[-1].time - samples[0].time
    return tuple((b - a) / elapsed for a, b in zip(samples[0].done, samples[-1].done))


def phase_rates(samples):
    both = [s for s in samples if all(s.started) and not any(s.finished)
            and s.time >= max(s.started) + 1]
    after_a = [s for s in samples if s.finished[0] and not s.finished[1]
               and s.time >= s.finished[0] + 0.5]
    return rates(both), rates(after_a)


class Display:
    def __init__(self, total, processes, cpu, started):
        self.total = total
        self.processes = processes
        self.cpu = cpu
        self.started = started
        self.previous = False

    def render(self, sample, speed):
        phase = "A finished; B runs alone" if sample.finished[0] and not sample.finished[1] else "A / B"
        lines = [f"elapsed={sample.time - self.started:5.1f}s  {phase}"]
        for i, name in enumerate(("race_a", "race_b")):
            percent = min(100, sample.done[i] * 100 / self.total)
            count = int(percent * 24 / 100)
            bar = "#" * count + "-" * (24 - count)
            current = "done" if sample.finished[i] else f"{speed[i] * 100 / self.total:5.1f}%/s"
            lines.append(f"{name} PID={self.processes[i].pid:<7} CPU={self.cpu} [{bar}] {percent:5.1f}%  {current}")
        if sys.stdout.isatty() and self.previous:
            print("\033[3F", end="")
        for line in lines:
            print(("\033[2K" if sys.stdout.isatty() else "") + line)
        sys.stdout.flush()
        self.previous = True


def print_summary(samples, released):
    both, after_a = phase_rates(samples)
    print("\nRates from completed work (startup and finish boundaries excluded):")
    if both and both[1] > 0:
        print(f"while_both: A={both[0]:.1f} units/s B={both[1]:.1f} units/s A/B={both[0] / both[1]:.2f}x")
    else:
        print("while_both: insufficient measurement time")
    if both and both[1] > 0 and after_a:
        print(f"after_A: B={after_a[1]:.1f} units/s B_speedup={after_a[1] / both[1]:.2f}x")
    else:
        print("after_A: insufficient measurement time (A must finish sufficiently before B)")
    for i, name in enumerate(("race_a", "race_b")):
        print(f"{name}_finished_s={samples[-1].finished[i] - released:.2f}")


def run(args):
    if sys.platform != "linux" or os.geteuid() != 0:
        raise RuntimeError("run this experiment as root inside the tutorial VM")
    if STATE.read_text().strip() != "disabled":
        raise RuntimeError("stop the running BPF scheduler before this experiment")
    if args.cpu not in os.sched_getaffinity(0):
        raise ValueError("the selected CPU is not available")
    check_other_tasks(args.cpu)
    calibration = subprocess.run([str(args.workload), "race-calibrate", "--cpu", str(args.cpu)],
                                 capture_output=True, text=True, check=True, timeout=10)
    total = max(1, round(int(calibration.stdout.strip()) * args.cpu_seconds))
    print(f"kernel={os.uname().release} scheduler={args.scheduler}")
    print(f"same_work={total} units each; CPU={args.cpu}; mode=partial", flush=True)

    processes = []
    with tempfile.TemporaryDirectory(prefix="scx-race-") as directory, ExitStack() as stack:
        log = stack.enter_context(tempfile.TemporaryFile(mode="w+"))
        scheduler = subprocess.Popen([str(args.scheduler), "--partial"], stdout=log, stderr=log)
        try:
            deadline = time.monotonic() + 5
            while STATE.read_text().strip() != "enabled":
                if scheduler.poll() is not None or time.monotonic() >= deadline:
                    raise RuntimeError("scheduler did not become active")
                time.sleep(0.05)
            maps = []
            for name in ("race_a", "race_b"):
                path = Path(directory) / name
                file = stack.enter_context(path.open("w+b"))
                file.truncate(32)
                maps.append(stack.enter_context(mmap.mmap(file.fileno(), 32)))
                process = subprocess.Popen([str(args.workload), "race-worker", "--name", name,
                                            "--units", str(total), "--cpu", str(args.cpu),
                                            "--progress", str(path)],
                                           stdin=subprocess.PIPE, stdout=log, stderr=log)
                processes.append(process)

            deadline = time.monotonic() + 5
            while not all(struct.unpack_from("=Q", page, 24)[0] for page in maps):
                if any(p.poll() is not None for p in processes) or time.monotonic() >= deadline:
                    raise RuntimeError("race workers did not become ready")
                time.sleep(0.05)
            for process in processes:
                name = Path(f"/proc/{process.pid}/comm").read_text().strip()
                print(f"ready: name={name} PID={process.pid} CPU={args.cpu}")
            check_other_tasks(args.cpu, {p.pid for p in processes})
            print("Starting both workers. Ctrl+C stops this experiment.", flush=True)
            released = time.monotonic()
            for process in processes:
                process.stdin.write(b"S")
                process.stdin.flush()
                process.stdin.close()
                process.stdin = None
            display = Display(total, processes, args.cpu, released)
            samples = []
            previous = read_sample(maps)
            display.render(previous, (0, 0))
            while True:
                time.sleep(0.1)
                sample = read_sample(maps)
                samples.append(sample)
                if scheduler.poll() is not None or STATE.read_text().strip() != "enabled":
                    raise RuntimeError("scheduler stopped during the race")
                for i, process in enumerate(processes):
                    result = process.poll()
                    if result is not None and (result != 0 or not sample.finished[i]):
                        raise RuntimeError(f"worker {process.pid} stopped without completing its work")
                if sample.time - previous.time >= 1 or all(sample.finished):
                    elapsed = sample.time - previous.time
                    speed = tuple((b - a) / elapsed for a, b in zip(previous.done, sample.done))
                    display.render(sample, speed)
                    previous = sample
                    check_other_tasks(args.cpu, {p.pid for p in processes})
                if all(sample.finished):
                    break
                if sample.time - released > 120:
                    raise RuntimeError("race exceeded 120 seconds; stopped both workers")
            print_summary(samples, released)
        finally:
            for process in processes:
                stop_process(process)
            stop_process(scheduler, signal.SIGINT)
            log.seek(0)
            print(log.read(), file=sys.stderr, end="")
            print(f"scheduler_state_after={STATE.read_text().strip()}", flush=True)


def main():
    def interrupted(signum, frame):
        raise KeyboardInterrupt

    signal.signal(signal.SIGTERM, interrupted)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scheduler", type=Path, required=True)
    parser.add_argument("--workload", type=Path, default=WORKLOAD)
    parser.add_argument("--cpu", type=int, default=0)
    parser.add_argument("--cpu-seconds", type=float, default=12,
                        help="approximate CPU seconds of fixed work per process (2 to 30)")
    args = parser.parse_args()
    if not 2 <= args.cpu_seconds <= 30:
        parser.error("--cpu-seconds must be between 2 and 30")
    run(args)


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, ValueError, OSError, subprocess.SubprocessError) as error:
        sys.exit(str(error))
    except KeyboardInterrupt:
        sys.exit(130)
