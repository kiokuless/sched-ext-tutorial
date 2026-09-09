#!/usr/bin/env bash
# SPDX-License-Identifier: MIT OR Apache-2.0
set -euo pipefail

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$repo_root"

mdbook build
mdbook test
cargo fmt --all --check
cargo test --workspace
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s scripts/tests

while IFS= read -r manifest; do
    cargo fmt --manifest-path "$manifest" --all --check
done < <(find lab checkpoints -name Cargo.toml -print | sort)

while IFS= read -r script; do
    bash -n "$script"
done < <(find scripts vm -type f -name '*.sh' -print | sort)

echo "Local checks passed. Scheduler builds require the tutorial VM."
