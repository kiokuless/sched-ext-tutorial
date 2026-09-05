#!/usr/bin/env bash
# SPDX-License-Identifier: MIT OR Apache-2.0
set -euo pipefail

if (( $# != 1 )); then
    echo "usage: $0 STEP" >&2
    exit 2
fi

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
step=$1
shopt -s nullglob
matches=("$repo_root"/checkpoints/step-"$step"-*)

if (( ${#matches[@]} != 1 )); then
    echo "expected exactly one checkpoint for STEP=$step" >&2
    exit 1
fi

cp "${matches[0]}/src/bpf/main.bpf.c" "$repo_root/lab/src/bpf/main.bpf.c"
printf 'Restored lab/src/bpf/main.bpf.c from %s\n' "${matches[0]#$repo_root/}"

