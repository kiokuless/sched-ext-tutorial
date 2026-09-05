#!/usr/bin/env bash
# SPDX-License-Identifier: MIT OR Apache-2.0
# Combine all tutorial Markdown files into a single document for AI reading.
set -euo pipefail

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
output="${1:-$repo_root/book/combined.md}"

cd "$repo_root/src"

# Extract relative paths from SUMMARY.md in menu order.
# Lines look like:  - [title](./path.md)
files=$(
    sed -n 's/.*(\.\/\(.*\.md\)).*/\1/p' SUMMARY.md
)

rm -f "$output"

for f in $files; do
    if [[ ! -f $f ]]; then
        echo "warning: $f not found, skipping" >&2
        continue
    fi

    {
        printf '\n---\n'
        printf '# %s\n\n' "$f"
        cat "$f"
        printf '\n'
    } >> "$output"
done

echo "combined $(echo "$files" | wc -l | tr -d ' ') files into $output"