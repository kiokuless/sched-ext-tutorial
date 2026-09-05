// SPDX-License-Identifier: GPL-2.0-only

fn main() {
    scx_cargo::BpfBuilder::new()
        .expect("failed to initialize the BPF builder")
        .enable_skel("src/bpf/main.bpf.c", "bpf")
        .build()
        .expect("failed to build the BPF scheduler");
}
