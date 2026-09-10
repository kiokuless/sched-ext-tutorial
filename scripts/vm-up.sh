#!/usr/bin/env bash
# SPDX-License-Identifier: MIT OR Apache-2.0
set -euo pipefail

vm_name=${VM_NAME:-sched-ext-lab}
vm_image=${SCHED_EXT_VM_IMAGE:-26.04}
repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)

if multipass info "$vm_name" >/dev/null 2>&1; then
    state=$(multipass info "$vm_name" --format csv | awk -F, 'NR == 2 { print $2 }')
    if [[ $state != Running ]]; then
        multipass start "$vm_name"
    fi
else
    multipass launch "$vm_image" \
        --name "$vm_name" \
        --cpus 4 \
        --memory 4G \
        --disk 20G
fi

VM_NAME="$vm_name" REPO_ROOT="$repo_root" bash "$repo_root/scripts/vm-mount.sh"

printf 'VM %s is ready. Run `make vm-bootstrap` on a fresh image.\n' "$vm_name"

