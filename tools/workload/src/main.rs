// SPDX-License-Identifier: MIT OR Apache-2.0

use std::hint::black_box;
use std::thread;
use std::time::{Duration, Instant};

#[cfg(target_os = "linux")]
use anyhow::Context;
use anyhow::{bail, Result};
use clap::{Parser, Subcommand};

#[cfg(target_os = "linux")]
const SCHED_EXT: libc::c_int = 7;

#[derive(Debug, Parser)]
#[command(about = "Controlled workloads for the sched_ext tutorial")]
struct Cli {
    #[command(subcommand)]
    command: Command,
}

#[derive(Debug, Subcommand)]
enum Command {
    /// Consume CPU time without sleeping.
    CpuHog {
        #[arg(long, default_value_t = 20)]
        seconds: u64,

        #[arg(long)]
        sched_ext: bool,
    },

    /// Wake periodically and report how late execution resumed.
    Periodic {
        #[arg(long, default_value_t = 1_000)]
        period_ms: u64,

        #[arg(long, default_value_t = 15)]
        samples: u64,

        #[arg(long, default_value_t = 100)]
        tolerance_ms: u64,

        #[arg(long)]
        sched_ext: bool,
    },
}

fn enter_sched_ext(enabled: bool) -> Result<()> {
    if !enabled {
        return Ok(());
    }

    #[cfg(target_os = "linux")]
    {
        let param = libc::sched_param { sched_priority: 0 };
        let result = unsafe { libc::sched_setscheduler(0, SCHED_EXT, &param) };
        if result != 0 {
            return Err(std::io::Error::last_os_error())
                .context("failed to move the process to SCHED_EXT");
        }
        Ok(())
    }

    #[cfg(not(target_os = "linux"))]
    {
        bail!("--sched-ext is available only on Linux")
    }
}

fn cpu_hog(seconds: u64, sched_ext: bool) -> Result<()> {
    enter_sched_ext(sched_ext)?;

    let deadline = Instant::now() + Duration::from_secs(seconds);
    let mut value = 1_u64;
    while Instant::now() < deadline {
        for _ in 0..100_000 {
            value = value.wrapping_mul(6364136223846793005).wrapping_add(1);
        }
        black_box(value);
    }

    Ok(())
}

fn periodic(period_ms: u64, samples: u64, tolerance_ms: u64, sched_ext: bool) -> Result<()> {
    if period_ms == 0 {
        bail!("--period-ms must be greater than zero");
    }
    if samples == 0 {
        bail!("--samples must be greater than zero");
    }

    enter_sched_ext(sched_ext)?;

    let period = Duration::from_millis(period_ms);
    let tolerance = Duration::from_millis(tolerance_ms);
    let mut target = Instant::now() + period;
    let mut total_late = Duration::ZERO;
    let mut max_late = Duration::ZERO;
    let mut misses = 0_u64;

    println!("sample,late_ms,deadline_missed");

    for sample in 1..=samples {
        thread::sleep(target.saturating_duration_since(Instant::now()));
        let resumed = Instant::now();
        let late = resumed.saturating_duration_since(target);
        let missed = late > tolerance;

        total_late += late;
        max_late = max_late.max(late);
        misses += u64::from(missed);

        println!("{sample},{:.3},{}", late.as_secs_f64() * 1_000.0, missed);
        target += period;
    }

    let average_ms = total_late.as_secs_f64() * 1_000.0 / samples as f64;
    println!();
    println!("average_late_ms={average_ms:.3}");
    println!("max_late_ms={:.3}", max_late.as_secs_f64() * 1_000.0);
    println!("deadline_misses={misses}/{samples}");

    Ok(())
}

fn main() -> Result<()> {
    match Cli::parse().command {
        Command::CpuHog { seconds, sched_ext } => cpu_hog(seconds, sched_ext),
        Command::Periodic {
            period_ms,
            samples,
            tolerance_ms,
            sched_ext,
        } => periodic(period_ms, samples, tolerance_ms, sched_ext),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn rejects_zero_period() {
        assert!(periodic(0, 1, 1, false).is_err());
    }

    #[test]
    fn rejects_zero_samples() {
        assert!(periodic(1, 0, 1, false).is_err());
    }
}
