#!/usr/bin/env bash
# SPDX-License-Identifier: MIT OR Apache-2.0
set -euo pipefail

if (( $# != 2 )); then
    echo "usage: $0 STEP partial|system" >&2
    exit 2
fi

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
step=$1
mode=$2

"$repo_root/scripts/guest/build-step.sh" "$step"
# Binary is built into the VM-local target directory to avoid macOS mount issues.
binary="/var/cache/sched-ext-tutorial/target/scx-step-$step/release/scx_oreore"

case "$mode" in
    partial)
        exec sudo "$binary" --partial
        ;;
    system)
        exec sudo "$binary"
        ;;
    *)
        echo "MODE must be partial or system" >&2
        exit 2
        ;;
esac

