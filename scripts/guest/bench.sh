#!/usr/bin/env bash
# SPDX-License-Identifier: MIT OR Apache-2.0
set -euo pipefail

if (( $# != 2 )); then
    echo "usage: $0 fair|step|dsq STEP" >&2
    exit 2
fi

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
case_name=$1
step=$2

if [[ $case_name == dsq ]]; then
    "$repo_root/scripts/guest/build-step.sh" "$step"
    "$repo_root/scripts/guest/build-workload.sh"
    exec sudo python3 "$repo_root/scripts/guest/dsq_experiment.py" \
        --scheduler "/var/cache/sched-ext-tutorial/target/scx-step-$step/release/scx_oreore"
fi

# Binary is built into the VM-local target directory to avoid macOS mount issues.
workload="/var/cache/sched-ext-tutorial/target/workload/release/sched-ext-workload"
scheduler_pid=
hog_pids=()
tmp_dir=$(mktemp -d)

cleanup() {
    # Kill all CPU hogs.
    for pid in "${hog_pids[@]:-}"; do
        sudo kill "$pid" >/dev/null 2>&1 || true
    done
    for pid in "${hog_pids[@]:-}"; do
        wait "$pid" >/dev/null 2>&1 || true
    done
    if [[ -n ${scheduler_pid:-} ]]; then
        sudo kill -INT "$scheduler_pid" >/dev/null 2>&1 || true
        wait "$scheduler_pid" >/dev/null 2>&1 || true
    fi
    rm -rf "$tmp_dir"
}
trap cleanup EXIT INT TERM

"$repo_root/scripts/guest/build-workload.sh"

sched_ext_args=()
if [[ $case_name == step ]]; then
    "$repo_root/scripts/guest/build-step.sh" "$step"
    scheduler="/var/cache/sched-ext-tutorial/target/scx-step-$step/release/scx_oreore"
    sudo "$scheduler" --partial >"$tmp_dir/scheduler.log" 2>&1 &
    scheduler_pid=$!
    sched_ext_args=(--sched-ext)

    for _ in {1..50}; do
        [[ $(cat /sys/kernel/sched_ext/state 2>/dev/null || true) == enabled ]] && break
        sleep 0.1
    done
    if [[ $(cat /sys/kernel/sched_ext/state 2>/dev/null || true) != enabled ]]; then
        cat "$tmp_dir/scheduler.log" >&2
        echo "scheduler did not become active" >&2
        exit 1
    fi
elif [[ $case_name != fair ]]; then
    echo "CASE must be fair, step or dsq" >&2
    exit 2
fi

# Start two CPU-bound hogs on CPU 0 so there is always contention
# for the same core.  With a single hog, the 10 ms slice shows little
# context-switch increase because there is no peer task to preempt it.
for _ in 1 2; do
    sudo taskset -c 0 "$workload" cpu-hog --seconds 60 "${sched_ext_args[@]}" &
    hog_pids+=("$!")
done
sleep 0.5

sudo perf stat -a -C 0 -e context-switches -o "$tmp_dir/perf.txt" -- \
    taskset -c 0 "$workload" sleep \
        --period-ms 1000 \
        --samples 5 \
        "${sched_ext_args[@]}"

echo
sed -n '/context-switches/p' "$tmp_dir/perf.txt"
