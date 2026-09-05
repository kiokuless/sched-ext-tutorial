# Repository Guidelines

## Project Structure & Module Organization

Book chapters live in `src/`; keep navigation synchronized in `src/SUMMARY.md`.
The editable scheduler is in `lab/`, while `checkpoints/step-NN-name/` contains buildable reference states.
`tools/workload/` provides the Rust benchmark workload.
Automation lives in `scripts/`, and VM provisioning lives in `vm/`.
Generated output belongs in `book/` or `target/` and must not be committed.

## Build, Test, and Development Commands

- `mdbook serve --open`: preview the tutorial; `make docs` renders `book/`.
- `make check`: build and test the book, check Rust formatting, run workload tests, and validate shell syntax.
- `make vm-up && make vm-bootstrap`: create and prepare the Multipass lab VM.
- `make doctor`: verify the VM requirements.
- `make build STEP=01`: build one checkpoint inside the VM; use `STEP=lab` for the editable scheduler.
- `make run STEP=01 MODE=partial`: load a scheduler, initially using partial switching.
- `make bench CASE=step STEP=03`: run the controlled latency experiment.
- `make verify-checkpoints`: build all checkpoints and the workload.

## Coding Style & Naming Conventions

Use `cargo fmt`; Rust files use four-space indentation and `snake_case` identifiers.
Follow Linux kernel style in BPF C, including tabs where the surrounding code uses them.
Shell scripts use Bash, `set -euo pipefail`, quoted variables, and `snake_case` names.
Name checkpoints `step-NN-short-description` and keep each one independently buildable.
Japanese prose uses one sentence per line and defines unfamiliar terms first.

## Testing Guidelines

Rust tests use the built-in harness and behavior names such as `rejects_zero_period`.
There is no coverage threshold; new workload behavior should include focused tests.
Run `make check` before every PR.
BPF, VM, or experiment changes also require `make doctor` and `make verify-checkpoints` in the supported VM.
Test scheduler load, unload, and recovery when relevant.

## Commit & Pull Request Guidelines

No commit convention exists yet.
Use short imperative subjects, optionally scoped, such as `docs: explain partial switching` or `lab: add shared DSQ`.
PRs should describe behavior changes, list commands run, and include measured experiment output.
Attach screenshots only for material layout changes.

## Safety & Licensing

Run schedulers as root only inside the disposable tutorial VM; never test them on the macOS host.
Do not modify or delete unrelated Multipass instances.
Preserve license boundaries: tutorial text is CC BY 4.0, original tooling is MIT OR Apache-2.0, and scheduler derivatives are GPL-2.0-only.
