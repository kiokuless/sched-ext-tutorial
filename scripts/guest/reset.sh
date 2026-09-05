#!/usr/bin/env bash
# SPDX-License-Identifier: MIT OR Apache-2.0
set -euo pipefail

state=$(cat /sys/kernel/sched_ext/state 2>/dev/null || true)
if [[ $state != enabled ]]; then
    echo "sched_ext is already disabled"
    exit 0
fi

ops=$(cat /sys/kernel/sched_ext/root/ops 2>/dev/null || true)
if [[ $ops != oreore* && $ops != oreore_broken* ]]; then
    echo "refusing to reset a scheduler not owned by this tutorial: $ops" >&2
    exit 1
fi

echo S | sudo tee /proc/sysrq-trigger >/dev/null

for _ in {1..50}; do
    [[ $(cat /sys/kernel/sched_ext/state 2>/dev/null || true) == disabled ]] && exit 0
    sleep 0.1
done

echo "sched_ext did not become disabled" >&2
exit 1

