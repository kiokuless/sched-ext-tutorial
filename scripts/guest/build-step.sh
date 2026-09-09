#!/usr/bin/env bash
# SPDX-License-Identifier: MIT OR Apache-2.0
set -euo pipefail

if (( $# != 1 )); then
    echo "usage: $0 STEP" >&2
    exit 2
fi

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
source "$repo_root/scripts/guest/resolve-step.sh"

step=$1
step_dir=$(resolve_step "$repo_root" "$step")
# Use the VM-local filesystem for build artifacts to avoid macOS mount issues.
target_dir="/var/cache/sched-ext-tutorial/target/scx-step-$step"

# Shared/restored sources can have older mtimes than the VM-local Cargo cache.
# Make BPF content changes invalidate the build script even in that case.
bpf_source_hash=$(sha256sum "$step_dir/src/bpf/main.bpf.c" | cut -d ' ' -f 1)

SCX_TUTORIAL_BPF_SOURCE_HASH="$bpf_source_hash" \
    BPF_CLANG=clang-19 CARGO_TARGET_DIR="$target_dir" \
    CARGO_INCREMENTAL=0 \
    cargo build --release --locked --offline --manifest-path "$step_dir/Cargo.toml"

