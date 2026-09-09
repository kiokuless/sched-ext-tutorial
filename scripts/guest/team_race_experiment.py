#!/usr/bin/env python3
# SPDX-License-Identifier: MIT OR Apache-2.0
"""Measure B1's progress before and after team A grows on one CPU in the lab VM."""

import argparse
from contextlib import ExitStack
import mmap
import os
from pathlib import Path
import signal
import struct
import subprocess
import sys
import tempfile
import time

from dsq_experiment import STATE, WORKLOAD, check_other_tasks, ensure_running, stop_process
from race_experiment import read_sample, rates


BEFORE_SECONDS = 5
AFTER_SECONDS = 8
WARMUP_SECONDS = 1


def phase_rates(samples, arrival):
    # Slots stay fixed: A1, B1, then A2..An. Newcomers have zero counters until
    # spawned. Exclude their creation as well as startup and any completion.
    before = [s for s in samples if s.time < arrival and all(s.started[:2])
              and not any(s.started[2:]) and not any(s.finished)
              and s.time >= max(s.started[:2]) + WARMUP_SECONDS]
    after = [s for s in samples if s.time >= arrival and all(s.started)
             and not any(s.finished)
             and s.time >= max(s.started) + WARMUP_SECONDS]
    return rates(before), rates(after)


class Display:
    def __init__(self, names, processes, total, cpu, released):
        self.names = names
        self.processes = processes
        self.total = total
        self.cpu = cpu
        self.released = released
        self.previous = False

    def render(self, sample, speed, added):
        phase = f"A: {len(self.names) - 1} members / B: 1 member" if added else "A1 / B1"
        lines = [f"elapsed={sample.time - self.released:5.1f}s  {phase}"]
        for i, name in enumerate(self.names):
            process = self.processes[i]
            if process is None:
                lines.append(f"{name} (not started)")
                continue
            percent = min(100, sample.done[i] * 100 / self.total)
            count = int(percent * 24 / 100)
            bar = "#" * count + "-" * (24 - count)
            lines.append(f"{name} PID={process.pid:<7} CPU={self.cpu} [{bar}] "
                         f"{percent:5.1f}%  {speed[i] * 100 / self.total:5.1f}%/s")
        if sys.stdout.isatty() and self.previous:
            print(f"\033[{len(lines)}F", end="")
        for line in lines:
            print(("\033[2K" if sys.stdout.isatty() else "") + line)
        sys.stdout.flush()
        self.previous = True


def print_summary(samples, arrival, a_members):
    before, after = phase_rates(samples, arrival)
    if before is None or after is None or before[1] <= 0:
        raise RuntimeError("insufficient progress to compare B1 before and after the arrival")
    print("\nRates from completed work (startup and arrival boundaries excluded):")
    for label, speed in (("before", before), ("after", after)):
        team_a = sum(speed) - speed[1]
        print(f"{label}: A_total={team_a:.1f} units/s B1={speed[1]:.1f} units/s")
    print(f"B_after/B_before={after[1] / before[1]:.2f}x  A_members=1->{a_members}")
    print("Measurement complete. Stopping all workers with unfinished work.", flush=True)


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
    # Keep every worker runnable throughout the two observation windows, even
    # if the learner's policy gives one worker nearly the whole CPU.
    total = max(1, int(calibration.stdout.strip()) * 30)
    names = ["team_a1", "team_b1"] + [f"team_a{i}" for i in range(2, args.a_members + 1)]
    processes = [None] * len(names)
    print(f"kernel={os.uname().release} scheduler={args.scheduler}")
    print(f"same_work={total} units each; CPU={args.cpu}; mode=partial")
    print(f"A_members=1->{args.a_members}; add_after={BEFORE_SECONDS}s; "
          f"observe_after={AFTER_SECONDS}s; Ctrl+C stops this experiment.", flush=True)

    def active():
        return [p for p in processes if p is not None]

    with tempfile.TemporaryDirectory(prefix="scx-team-race-") as directory, ExitStack() as stack:
        log = stack.enter_context(tempfile.TemporaryFile(mode="w+"))
        paths = [Path(directory) / name for name in names]
        maps = []
        for path in paths:
            file = stack.enter_context(path.open("w+b"))
            file.truncate(32)
            maps.append(stack.enter_context(mmap.mmap(file.fileno(), 32)))
        scheduler = subprocess.Popen([str(args.scheduler), "--partial"], stdout=log, stderr=log)
        try:
            deadline = time.monotonic() + 5
            while STATE.read_text().strip() != "enabled":
                if scheduler.poll() is not None or time.monotonic() >= deadline:
                    raise RuntimeError("scheduler did not become active")
                time.sleep(0.05)

            def start_batch(indices):
                for i in indices:
                    processes[i] = subprocess.Popen(
                        [str(args.workload), "race-worker", "--name", names[i],
                         "--units", str(total), "--cpu", str(args.cpu), "--progress", str(paths[i])],
                        stdin=subprocess.PIPE, stdout=log, stderr=log)
                deadline = time.monotonic() + 5
                while not all(struct.unpack_from("=Q", maps[i], 24)[0] for i in indices):
                    ensure_running(scheduler, active())
                    if time.monotonic() >= deadline:
                        raise RuntimeError("team workers did not become ready")
                    time.sleep(0.05)
                for i in indices:
                    name = Path(f"/proc/{processes[i].pid}/comm").read_text().strip()
                    print(f"ready: name={name} PID={processes[i].pid} CPU={args.cpu}")
                check_other_tasks(args.cpu, {p.pid for p in active()})
                for i in indices:
                    process = processes[i]
                    process.stdin.write(b"S")
                    process.stdin.flush()
                    process.stdin.close()
                    process.stdin = None
                sys.stdout.flush()

            start_batch(range(2))
            released = time.monotonic()
            startup_deadline = released + 5
            arrival = None
            samples = []
            previous = read_sample(maps)
            display = Display(names, processes, total, args.cpu, released)
            display.render(previous, (0,) * len(names), False)
            while True:
                time.sleep(0.1)
                sample = read_sample(maps)
                samples.append(sample)
                ensure_running(scheduler, active())
                if any(sample.finished):
                    raise RuntimeError("a worker finished too early; repeat the measurement")
                expected = sample.started[:2] if arrival is None else sample.started
                if not all(expected) and sample.time >= startup_deadline:
                    raise RuntimeError("team workers did not start computing")
                if arrival is None and all(expected) and sample.time >= max(expected) + BEFORE_SECONDS:
                    # Freeze the before window before creating any new task.
                    arrival = time.monotonic()
                    print(f"\nAdding {', '.join(names[2:])} at {arrival - released:.1f}s", flush=True)
                    display.previous = False
                    start_batch(range(2, len(names)))
                    startup_deadline = time.monotonic() + 5
                    previous = read_sample(maps)
                    continue
                complete = (arrival is not None and all(expected)
                            and sample.time >= max(expected) + AFTER_SECONDS)
                if sample.time - previous.time >= 1 or complete:
                    elapsed = sample.time - previous.time
                    speed = tuple((b - a) / elapsed for a, b in zip(previous.done, sample.done))
                    display.render(sample, speed, arrival is not None)
                    previous = sample
                    check_other_tasks(args.cpu, {p.pid for p in active()})
                if complete:
                    print_summary(samples, arrival, args.a_members)
                    break
                if sample.time - released > 30:
                    raise RuntimeError("team experiment exceeded 30 seconds")
        finally:
            for process in active():
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
    parser.add_argument("--a-members", type=int, default=3,
                        help="team A size after the arrival (2 to 7)")
    args = parser.parse_args()
    if not 2 <= args.a_members <= 7:
        parser.error("--a-members must be between 2 and 7")
    run(args)


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, ValueError, OSError, subprocess.SubprocessError) as error:
        sys.exit(str(error))
    except KeyboardInterrupt:
        sys.exit(130)
