#!/usr/bin/env python3
# SPDX-License-Identifier: MIT OR Apache-2.0
"""Compare CPU shares with controlled PID parity on the tutorial VM."""

import argparse
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time


STATE = Path("/sys/kernel/sched_ext/state")
WORKLOAD = Path("/var/cache/sched-ext-tutorial/target/workload/release/sched-ext-workload")
SCHED_EXT = 7


def task_state(stat):
    # comm can contain spaces and parentheses. Fields after its final ')' start
    # with state (field 3).
    _, separator, fields = stat.rpartition(")")
    if not separator:
        raise ValueError("invalid /proc/PID/stat")
    fields = fields.split()
    return fields[0]


def read_runtime_ns(pid):
    return int(Path(f"/proc/{pid}/schedstat").read_text().split()[0])


def check_other_tasks(cpu, allowed=()):
    conflicts = []
    for stat_file in Path("/proc").glob("[0-9]*/task/[0-9]*/stat"):
        tid = int(stat_file.parent.name)
        if tid in allowed:
            continue
        try:
            if (os.sched_getscheduler(tid) == SCHED_EXT
                    and cpu in os.sched_getaffinity(tid)
                    and task_state(stat_file.read_text()) not in ("T", "t", "Z")):
                conflicts.append(tid)
        except (ProcessLookupError, FileNotFoundError):
            continue
    if conflicts:
        raise RuntimeError(f"other SCHED_EXT tasks can use CPU {cpu}: {sorted(conflicts)}; "
                           "stop those workloads before this experiment")


def stop_process(process, sig=signal.SIGTERM):
    if process.poll() is None:
        process.send_signal(sig)
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
    if process.stdin is not None:
        process.stdin.close()


def choose_workers(even, odd, spawn):
    remaining = [even, odd]
    selected = []
    try:
        # Do not assume successive PIDs alternate: other VM processes may fork.
        for _ in range(256):
            if not any(remaining):
                return selected
            process = spawn()
            parity = process.pid % 2
            if remaining[parity]:
                selected.append(process)
                remaining[parity] -= 1
            else:
                stop_process(process)
        if not any(remaining):
            return selected
        raise RuntimeError("could not obtain the requested PID parity counts")
    except BaseException:
        for process in selected:
            stop_process(process)
        raise


def ensure_running(scheduler, workers):
    if scheduler.poll() is not None or STATE.read_text().strip() != "enabled":
        raise RuntimeError("scheduler stopped during the experiment")
    if any(process.poll() is not None for process in workers):
        raise RuntimeError("a CPU worker stopped before measurement completed")


def run_experiment(args):
    if sys.platform != "linux" or os.geteuid() != 0:
        raise RuntimeError("run this experiment as root inside the tutorial VM")
    if STATE.read_text().strip() != "disabled":
        raise RuntimeError("stop the running BPF scheduler before this experiment")
    if args.cpu not in os.sched_getaffinity(0):
        raise ValueError("the selected CPU is not available")
    check_other_tasks(args.cpu)

    workers = []
    with tempfile.TemporaryFile(mode="w+") as log:
        scheduler = subprocess.Popen(
            [str(args.scheduler), "--partial"], stdout=log, stderr=log
        )
        try:
            deadline = time.monotonic() + 5
            while STATE.read_text().strip() != "enabled":
                if scheduler.poll() is not None or time.monotonic() >= deadline:
                    raise RuntimeError("scheduler did not become active")
                time.sleep(0.05)

            def spawn():
                # The wrapper waits on stdin, then execs the existing Rust hog.
                # exec preserves its PID, so parity is known before it can run.
                return subprocess.Popen(
                    [sys.executable, str(Path(__file__).resolve()), "--worker",
                     "--workload", str(args.workload), "--cpu", str(args.cpu),
                     "--seconds", str(args.seconds + 30)],
                    stdin=subprocess.PIPE, stdout=log, stderr=log,
                )

            workers = choose_workers(args.even, args.odd, spawn)
            for process in workers:
                process.stdin.write(b"S")
                process.stdin.flush()
                process.stdin.close()
                process.stdin = None

            deadline = time.monotonic() + 5
            while True:
                ensure_running(scheduler, workers)
                if all(os.sched_getscheduler(p.pid) == SCHED_EXT for p in workers):
                    break
                if time.monotonic() >= deadline:
                    raise RuntimeError("workers did not enter SCHED_EXT")
                time.sleep(0.05)
            time.sleep(1)
            ensure_running(scheduler, workers)
            check_other_tasks(args.cpu, {p.pid for p in workers})

            before = {p.pid: read_runtime_ns(p.pid) for p in workers}
            started = time.monotonic()
            time.sleep(args.seconds)
            ensure_running(scheduler, workers)
            runtimes = {p.pid: read_runtime_ns(p.pid) - before[p.pid] for p in workers}
            elapsed = time.monotonic() - started
            check_other_tasks(args.cpu, {p.pid for p in workers})
            total = sum(runtimes.values())
            if total == 0:
                raise RuntimeError("no worker CPU time was recorded")

            print(f"kernel={os.uname().release}")
            print(f"scheduler={args.scheduler}")
            print(f"cpu={args.cpu},even={args.even},odd={args.odd},elapsed_s={elapsed:.3f}")
            print("pid,parity,cpu_ms,share_percent")
            for pid in sorted(runtimes, key=lambda pid: (pid % 2, pid)):
                parity = "even" if pid % 2 == 0 else "odd"
                print(f"{pid},{parity},{runtimes[pid] / 1_000_000:.1f},{runtimes[pid] * 100 / total:.1f}")
            for parity, label in enumerate(("even", "odd")):
                subtotal = sum(value for pid, value in runtimes.items() if pid % 2 == parity)
                print(f"{label}_share_percent={subtotal * 100 / total:.1f}")
        finally:
            for process in workers:
                stop_process(process)
            stop_process(scheduler, signal.SIGINT)
            log.seek(0)
            print(log.read(), file=sys.stderr, end="")
            print(f"scheduler_state_after={STATE.read_text().strip()}")


def main():
    def interrupted(signum, frame):
        raise KeyboardInterrupt

    signal.signal(signal.SIGTERM, interrupted)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scheduler", type=Path)
    parser.add_argument("--workload", type=Path, default=WORKLOAD)
    parser.add_argument("--cpu", type=int, default=0)
    parser.add_argument("--even", type=int, default=3)
    parser.add_argument("--odd", type=int, default=1)
    parser.add_argument("--seconds", type=float, default=10)
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    max_seconds = 90 if args.worker else 60
    if not (0 < args.seconds <= max_seconds):
        parser.error(f"--seconds must be greater than zero and at most {max_seconds}")
    if min(args.even, args.odd) < 0 or not (0 < args.even + args.odd <= 32):
        parser.error("request between 1 and 32 workers with nonnegative parity counts")
    if args.worker:
        if sys.stdin.buffer.read(1) != b"S":
            raise RuntimeError("worker start gate was closed")
        os.sched_setaffinity(0, {args.cpu})
        os.execv(args.workload, [str(args.workload), "cpu-hog", "--seconds",
                                str(int(args.seconds)), "--sched-ext"])
    if args.scheduler is None:
        parser.error("--scheduler is required")
    run_experiment(args)


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, ValueError, OSError) as error:
        sys.exit(str(error))
    except KeyboardInterrupt:
        sys.exit(130)
