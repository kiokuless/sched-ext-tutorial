#!/usr/bin/env bash
# SPDX-License-Identifier: MIT OR Apache-2.0
set -euo pipefail

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)

for step_dir in "$repo_root"/checkpoints/step-*; do
    step_name=${step_dir##*/step-}
    step=${step_name%%-*}
    "$repo_root/scripts/guest/build-step.sh" "$step"
done

"$repo_root/scripts/guest/build-workload.sh"
echo "All checkpoints and the workload built successfully."
