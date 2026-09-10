#!/usr/bin/env bash
# SPDX-License-Identifier: MIT OR Apache-2.0
set -euo pipefail

if (( $# != 3 )); then
    echo "usage: $0 STEP CPU TEAM_A_MEMBERS" >&2
    exit 2
fi

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
bash "$repo_root/scripts/guest/build-step.sh" "$1"
bash "$repo_root/scripts/guest/build-workload.sh"
exec sudo python3 -B "$repo_root/scripts/guest/team_race_experiment.py" \
    --scheduler "/var/cache/sched-ext-tutorial/target/scx-step-$1/release/scx_oreore" \
    --cpu "$2" --a-members "$3"
