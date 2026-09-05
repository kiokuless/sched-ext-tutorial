#!/usr/bin/env bash
# SPDX-License-Identifier: MIT OR Apache-2.0
set -euo pipefail

vm_name=${VM_NAME:-sched-ext-lab}
repo_root=${REPO_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}
guest_root=/workspace/sched-ext-tutorial

if multipass info "$vm_name" | grep -Fq "$guest_root"; then
    exit 0
fi

multipass mount "$repo_root" "$vm_name:$guest_root"

