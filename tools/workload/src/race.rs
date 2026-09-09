// SPDX-License-Identifier: MIT OR Apache-2.0

#[cfg(any(target_os = "linux", test))]
fn work_unit(mut value: u64) -> u64 {
    for _ in 0..100_000 {
        value = value.rotate_left(7).wrapping_mul(6364136223846793005) ^ 0x9e3779b97f4a7c15;
    }
    std::hint::black_box(value)
}

#[cfg(any(target_os = "linux", test))]
fn fixed_work(units: u64, mut report: impl FnMut(u64)) -> anyhow::Result<()> {
    anyhow::ensure!(units > 0, "--units must be greater than zero");
    let mut value = 1;
    for completed in 1..=units {
        value = work_unit(value);
        report(completed);
    }
    Ok(())
}

#[cfg(target_os = "linux")]
mod linux {
    use std::ffi::CString;
    use std::fs::OpenOptions;
    use std::io::Read;
    use std::os::fd::AsRawFd;
    use std::path::Path;
    use std::sync::atomic::{AtomicU64, Ordering};

    use anyhow::{ensure, Context, Result};

    // Shared with race_experiment.py: completed, started_ns, finished_ns, ready.
    // The mmap counter avoids blocking pipe writes or sleep calls in the work loop.
    const PROGRESS_SIZE: usize = 32;
    struct Progress(*mut libc::c_void);

    impl Progress {
        fn open(path: &Path) -> Result<Self> {
            let file = OpenOptions::new().read(true).write(true).open(path)?;
            ensure!(
                file.metadata()?.len() >= PROGRESS_SIZE as u64,
                "progress file is too short"
            );
            // SAFETY: the file covers the requested length; mmap supplies aligned storage.
            let ptr = unsafe {
                libc::mmap(
                    std::ptr::null_mut(),
                    PROGRESS_SIZE,
                    libc::PROT_READ | libc::PROT_WRITE,
                    libc::MAP_SHARED,
                    file.as_raw_fd(),
                    0,
                )
            };
            if ptr == libc::MAP_FAILED {
                return Err(std::io::Error::last_os_error()).context("map progress file");
            }
            Ok(Self(ptr))
        }

        fn store(&self, index: usize, value: u64) {
            // SAFETY: the mapping contains four aligned, initially zero u64 values.
            // Only this worker writes them; the observer reads the shared mapping.
            let fields = unsafe { &*self.0.cast::<[AtomicU64; 4]>() };
            fields[index].store(value, Ordering::Release);
        }
    }

    impl Drop for Progress {
        fn drop(&mut self) {
            // SAFETY: this object owns the live mapping returned by mmap.
            unsafe {
                libc::munmap(self.0, PROGRESS_SIZE);
            }
        }
    }

    fn clock_ns(clock: libc::clockid_t) -> Result<u64> {
        let mut value = libc::timespec {
            tv_sec: 0,
            tv_nsec: 0,
        };
        // SAFETY: value is writable storage for a timespec.
        if unsafe { libc::clock_gettime(clock, &mut value) } != 0 {
            return Err(std::io::Error::last_os_error()).context("read race clock");
        }
        Ok(value.tv_sec as u64 * 1_000_000_000 + value.tv_nsec as u64)
    }

    fn pin_cpu(cpu: usize) -> Result<()> {
        ensure!(cpu < libc::CPU_SETSIZE as usize, "CPU number is too large");
        // SAFETY: CPU_SET receives a valid index and a correctly sized initialized set.
        let result = unsafe {
            let mut set: libc::cpu_set_t = std::mem::zeroed();
            libc::CPU_ZERO(&mut set);
            libc::CPU_SET(cpu, &mut set);
            libc::sched_setaffinity(0, std::mem::size_of_val(&set), &set)
        };
        if result != 0 {
            return Err(std::io::Error::last_os_error()).context("pin race worker");
        }
        Ok(())
    }

    pub fn calibrate(cpu: usize) -> Result<()> {
        pin_cpu(cpu)?;
        let start = clock_ns(libc::CLOCK_PROCESS_CPUTIME_ID)?;
        let mut units = 0_u64;
        let mut value = 1;
        loop {
            value = super::work_unit(value);
            units += 1;
            let elapsed = clock_ns(libc::CLOCK_PROCESS_CPUTIME_ID)? - start;
            if elapsed >= 250_000_000 {
                println!("{}", units * 1_000_000_000 / elapsed);
                return Ok(());
            }
        }
    }

    pub fn worker(name: &str, units: u64, cpu: usize, path: &Path) -> Result<()> {
        ensure!(units > 0, "--units must be greater than zero");
        ensure!(
            !name.is_empty() && name.len() <= 15,
            "name must be 1 to 15 bytes"
        );
        let name = CString::new(name)?;
        pin_cpu(cpu)?;
        // SAFETY: name is a terminated string alive for the duration of the call.
        if unsafe { libc::prctl(libc::PR_SET_NAME, name.as_ptr(), 0, 0, 0) } != 0 {
            return Err(std::io::Error::last_os_error()).context("set race process name");
        }
        let progress = Progress::open(path)?;
        progress.store(3, 1);
        let mut gate = [0_u8];
        std::io::stdin().read_exact(&mut gate)?;
        ensure!(gate == [b'S'], "worker start gate was closed");
        crate::enter_sched_ext(true)?;
        progress.store(1, clock_ns(libc::CLOCK_MONOTONIC)?);
        super::fixed_work(units, |done| progress.store(0, done))?;
        progress.store(2, clock_ns(libc::CLOCK_MONOTONIC)?);
        Ok(())
    }
}

#[cfg(target_os = "linux")]
pub use linux::{calibrate, worker};

#[cfg(not(target_os = "linux"))]
pub fn calibrate(_cpu: usize) -> anyhow::Result<()> {
    anyhow::bail!("run the A/B experiment inside the tutorial Linux VM")
}

#[cfg(not(target_os = "linux"))]
pub fn worker(
    _name: &str,
    _units: u64,
    _cpu: usize,
    _path: &std::path::Path,
) -> anyhow::Result<()> {
    anyhow::bail!("run the A/B experiment inside the tutorial Linux VM")
}

#[cfg(test)]
mod tests {
    #[test]
    fn finishes_exact_work_and_reports_all_completed_units() {
        let mut completed = Vec::new();
        super::fixed_work(3, |done| completed.push(done)).unwrap();
        assert_eq!(completed, [1, 2, 3]);
    }

    #[test]
    fn rejects_empty_work_before_reporting_progress() {
        assert!(super::fixed_work(0, |_| panic!("no work should be reported")).is_err());
    }
}
