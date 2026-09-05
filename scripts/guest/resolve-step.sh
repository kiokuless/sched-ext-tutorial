#!/usr/bin/env bash
# SPDX-License-Identifier: MIT OR Apache-2.0

resolve_step() {
    local repo_root=$1
    local step=$2
    local matches=()

    if [[ $step == lab ]]; then
        printf '%s\n' "$repo_root/lab"
        return 0
    fi

    shopt -s nullglob
    matches=("$repo_root"/checkpoints/step-"$step"-*)
    shopt -u nullglob

    if (( ${#matches[@]} != 1 )); then
        echo "expected exactly one checkpoint for STEP=$step" >&2
        return 1
    fi

    printf '%s\n' "${matches[0]}"
}
