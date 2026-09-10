// SPDX-License-Identifier: GPL-2.0-only

fn main() {
    println!("cargo:rerun-if-env-changed=SCX_TUTORIAL_BPF_SOURCE_HASH");
    scx_cargo::BpfBuilder::new()
        .expect("failed to initialize the BPF builder")
        .enable_skel("src/bpf/main.bpf.c", "bpf")
        .build()
        .expect("failed to build the BPF scheduler");
}
