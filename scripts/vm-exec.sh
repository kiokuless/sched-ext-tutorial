#!/usr/bin/env bash
# SPDX-License-Identifier: MIT OR Apache-2.0
set -euo pipefail

vm_name=${VM_NAME:-sched-ext-lab}
guest_root=/workspace/sched-ext-tutorial

if (( $# == 0 )); then
    set -- bash
fi

exec multipass exec --working-directory "$guest_root" "$vm_name" -- "$@"

