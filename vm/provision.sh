#!/usr/bin/env bash
# SPDX-License-Identifier: MIT OR Apache-2.0
set -euo pipefail

if (( EUID != 0 )); then
    echo "run this script as root" >&2
    exit 1
fi

tutorial_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
export DEBIAN_FRONTEND=noninteractive

apt-get update
apt-get install -y \
    bpftool \
    build-essential \
    ca-certificates \
    clang-19 \
    curl \
    git \
    jq \
    libbpf-dev \
    libelf-dev \
    linux-tools-common \
    llvm-19 \
    pkg-config

# Install the perf binary matching the running kernel.
# Avoids linux-tools-generic which pulls a full kernel image.
apt-get install -y "linux-tools-$(uname -r)"

ln -sfn /usr/bin/clang-19 /usr/local/bin/clang
ln -sfn /usr/bin/llvm-config-19 /usr/local/bin/llvm-config

if ! sudo -H -u ubuntu test -x /home/ubuntu/.cargo/bin/rustup; then
    rustup_installer=/tmp/sched-ext-rustup-init.sh
    curl --proto '=https' --tlsv1.2 -fsS https://sh.rustup.rs -o "$rustup_installer"
    chmod 0755 "$rustup_installer"
    sudo -H -u ubuntu "$rustup_installer" \
        -y \
        --no-modify-path \
        --profile minimal \
        --default-toolchain 1.95.0
    rm -f "$rustup_installer"
fi

for binary in cargo rustc rustfmt rustup; do
    if [[ -x /home/ubuntu/.cargo/bin/$binary ]]; then
        ln -sfn "/home/ubuntu/.cargo/bin/$binary" "/usr/local/bin/$binary"
    fi
done

# Pre-fetch crate dependencies for offline builds as the ubuntu user.
# Each checkpoint and lab has its own Cargo.lock; fetch into the shared
# cargo registry so that all subsequent builds succeed with --locked --offline.
sudo -H -u ubuntu env \
    PATH="/home/ubuntu/.cargo/bin:$PATH" \
    HOME=/home/ubuntu \
    bash -c '
for manifest in "$0"/lab/Cargo.toml \
                "$0"/checkpoints/step-*/Cargo.toml \
                "$0"/tools/workload/Cargo.toml; do
    [ -f "$manifest" ] || continue
    CARGO_TARGET_DIR=/tmp/sched-ext-fetch \
        cargo fetch --locked --manifest-path "$manifest"
done
' "$tutorial_root"

install -d /etc/sched-ext-tutorial
# Ensure the build-cache directory exists and is owned by ubuntu.
# This directory is used as CARGO_TARGET_DIR for all tutorial builds.
install -d -o ubuntu -g ubuntu /var/cache/sched-ext-tutorial/target
# Fix ownership on existing directories in case they were created earlier.
chown ubuntu:ubuntu /var/cache/sched-ext-tutorial/target 2>/dev/null || true
{
    printf 'ubuntu=%s\n' "$(. /etc/os-release && printf '%s' "$VERSION_ID")"
    printf 'kernel=%s\n' "$(uname -r)"
    printf 'scx=%s\n' '1.1.3'
    printf 'clang=%s\n' "$(clang-19 --version | head -n 1)"
    printf 'rust=%s\n' "$(rustc --version)"
    printf 'libbpf=%s\n' "$(pkg-config --modversion libbpf)"
    printf 'bpftool=%s\n' "$(bpftool version | head -n 1)"
    printf 'perf=%s\n' "$(perf --version 2>/dev/null | head -n 1 || echo 'not found')"
} > /etc/sched-ext-tutorial/versions

echo "Provisioning finished. The VM is ready with the stock kernel."
