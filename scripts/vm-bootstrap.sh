#!/usr/bin/env bash
# SPDX-License-Identifier: MIT OR Apache-2.0
set -euo pipefail

vm_name=${VM_NAME:-sched-ext-lab}
repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)

VM_NAME="$vm_name" bash "$repo_root/scripts/vm-exec.sh" sudo bash ./vm/provision.sh
VM_NAME="$vm_name" bash "$repo_root/scripts/vm-exec.sh" bash ./scripts/guest/doctor.sh
VM_NAME="$vm_name" bash "$repo_root/scripts/vm-exec.sh" bash ./scripts/guest/verify-checkpoints.sh

