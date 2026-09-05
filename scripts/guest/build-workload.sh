#!/usr/bin/env bash
# SPDX-License-Identifier: MIT OR Apache-2.0
set -euo pipefail

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
target_dir="/var/cache/sched-ext-tutorial/target/workload"
CARGO_TARGET_DIR="$target_dir" CARGO_INCREMENTAL=0 \
    cargo build --release --locked --offline -p sched-ext-workload

