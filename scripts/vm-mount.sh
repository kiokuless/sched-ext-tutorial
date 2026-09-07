#!/usr/bin/env bash
# SPDX-License-Identifier: MIT OR Apache-2.0
set -euo pipefail

vm_name=${VM_NAME:-sched-ext-lab}
repo_root=${REPO_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}
guest_root=/workspace/sched-ext-tutorial

case "$(uname -s)" in
    MSYS*|MINGW*)
        # Convert only the host path; the mount target is a Linux path.
        repo_root=$(cygpath -m "$repo_root")
        export MSYS2_ARG_CONV_EXCL='*'
        ;;
esac

if multipass info "$vm_name" | grep -Fq "$guest_root"; then
    exit 0
fi

multipass mount "$repo_root" "$vm_name:$guest_root"
