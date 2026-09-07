#!/usr/bin/env bash
# SPDX-License-Identifier: MIT OR Apache-2.0
set -euo pipefail

failed=0

check_equal() {
    local label=$1
    local actual=$2
    local expected=$3

    if [[ $actual == "$expected" ]]; then
        printf 'ok   %-18s %s\n' "$label" "$actual"
    else
        printf 'fail %-18s expected %s, got %s\n' "$label" "$expected" "$actual"
        failed=1
    fi
}

check_command() {
    local command=$1
    if command -v "$command" >/dev/null 2>&1; then
        printf 'ok   %-18s %s\n' "$command" "$(command -v "$command")"
    else
        printf 'fail %-18s not found\n' "$command"
        failed=1
    fi
}

architecture=$(uname -m)
case "$architecture" in
    aarch64|x86_64)
        printf 'ok   %-18s %s\n' architecture "$architecture"
        ;;
    *)
        printf 'fail %-18s expected aarch64 or x86_64, got %s\n' architecture "$architecture"
        failed=1
        ;;
esac
check_equal vcpus "$(nproc)" 4

if zgrep -q 'CONFIG_SCHED_CLASS_EXT=y' /proc/config.gz 2>/dev/null; then
    printf 'ok   %-18s CONFIG_SCHED_CLASS_EXT=y\n' sched_ext_config
elif [[ -f /boot/config-$(uname -r) ]] && grep -q 'CONFIG_SCHED_CLASS_EXT=y' "/boot/config-$(uname -r)"; then
    printf 'ok   %-18s CONFIG_SCHED_CLASS_EXT=y\n' sched_ext_config
else
    printf 'fail %-18s CONFIG_SCHED_CLASS_EXT not enabled\n' sched_ext_config
    failed=1
fi

for command in clang-19 cargo bpftool perf taskset; do
    check_command "$command"
done

if [[ -r /sys/kernel/sched_ext/state ]]; then
    printf 'ok   %-18s %s\n' sched_ext "$(cat /sys/kernel/sched_ext/state)"
else
    printf 'fail %-18s unavailable\n' sched_ext
    failed=1
fi

if [[ -r /sys/kernel/btf/vmlinux ]]; then
    printf 'ok   %-18s available\n' BTF
else
    printf 'fail %-18s unavailable\n' BTF
    failed=1
fi

if (( failed != 0 )); then
    exit 1
fi

echo "The tutorial VM is ready."

