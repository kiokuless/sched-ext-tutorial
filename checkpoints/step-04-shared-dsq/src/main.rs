// SPDX-License-Identifier: GPL-2.0-only

mod bpf_skel;

use std::mem::MaybeUninit;
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::Arc;
use std::thread;
use std::time::Duration;

use anyhow::{Context, Result};
use bpf_skel::*;
use clap::Parser;
use libbpf_rs::OpenObject;
use scx_utils::compat;
use scx_utils::libbpf_clap_opts::LibbpfOpts;
use scx_utils::{scx_ops_attach, scx_ops_load, scx_ops_open};
use scx_utils::{try_set_rlimit_infinity, uei_exited, uei_report};

#[derive(Debug, Parser)]
#[command(about = "A small sched_ext scheduler for the tutorial")]
struct Opts {
    /// Switch only tasks that explicitly select SCHED_EXT.
    #[arg(long)]
    partial: bool,

    /// Override the scheduling slice in microseconds.
    #[arg(long)]
    slice_us: Option<u64>,

    /// Print libbpf debug messages.
    #[arg(short, long)]
    verbose: bool,

    #[command(flatten)]
    libbpf: LibbpfOpts,
}

fn main() -> Result<()> {
    let opts = Opts::parse();
    try_set_rlimit_infinity();

    let shutdown = Arc::new(AtomicBool::new(false));
    let shutdown_for_signal = shutdown.clone();
    ctrlc::set_handler(move || shutdown_for_signal.store(true, Ordering::Relaxed))
        .context("failed to install the signal handler")?;

    let mut open_object = MaybeUninit::<OpenObject>::uninit();

    loop {
        let mut builder = BpfSkelBuilder::default();
        builder.obj_builder.debug(opts.verbose);

        let open_opts = opts.libbpf.clone().into_bpf_open_opts();
        let mut skel = scx_ops_open!(builder, &mut open_object, oreore_ops, open_opts)?;

        if let Some(slice_us) = opts.slice_us {
            skel.maps.rodata_data.as_mut().unwrap().slice_ns = slice_us * 1_000;
        }
        if opts.partial {
            skel.struct_ops.oreore_ops_mut().flags |= *compat::SCX_OPS_SWITCH_PARTIAL;
        }

        let mut skel = scx_ops_load!(skel, oreore_ops, uei)?;
        let link = scx_ops_attach!(skel, oreore_ops)?;

        eprintln!(
            "scx_oreore started (mode={}, slice={} us)",
            if opts.partial {
                "partial"
            } else {
                "system-wide"
            },
            skel.maps.rodata_data.as_ref().unwrap().slice_ns / 1_000,
        );

        while !shutdown.load(Ordering::Relaxed) && !uei_exited!(&skel, uei) {
            thread::sleep(Duration::from_millis(250));
        }

        drop(link);
        let exit_info = uei_report!(&skel, uei)?;
        if shutdown.load(Ordering::Relaxed) || !exit_info.should_restart() {
            break;
        }
    }

    Ok(())
}
