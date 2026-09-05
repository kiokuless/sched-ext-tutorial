SHELL := /bin/bash

VM_NAME ?= sched-ext-lab
STEP ?= 01
MODE ?= partial
CASE ?= step

.PHONY: vm-up vm-mount vm-bootstrap vm-shell vm-stop doctor build run bench reset restore verify-checkpoints docs combine-docs test check

vm-up:
	VM_NAME="$(VM_NAME)" ./scripts/vm-up.sh

vm-mount:
	VM_NAME="$(VM_NAME)" ./scripts/vm-mount.sh

vm-bootstrap:
	VM_NAME="$(VM_NAME)" ./scripts/vm-bootstrap.sh

vm-shell:
	multipass shell "$(VM_NAME)"

vm-stop:
	multipass stop "$(VM_NAME)"

doctor:
	VM_NAME="$(VM_NAME)" ./scripts/vm-exec.sh ./scripts/guest/doctor.sh

build:
	VM_NAME="$(VM_NAME)" ./scripts/vm-exec.sh ./scripts/guest/build-step.sh "$(STEP)"

run:
	VM_NAME="$(VM_NAME)" ./scripts/vm-exec.sh ./scripts/guest/run-step.sh "$(STEP)" "$(MODE)"

bench:
	VM_NAME="$(VM_NAME)" ./scripts/vm-exec.sh ./scripts/guest/bench.sh "$(CASE)" "$(STEP)"

reset:
	VM_NAME="$(VM_NAME)" ./scripts/vm-exec.sh ./scripts/guest/reset.sh

restore:
	./scripts/restore-step.sh "$(STEP)"

verify-checkpoints:
	VM_NAME="$(VM_NAME)" ./scripts/vm-exec.sh ./scripts/guest/verify-checkpoints.sh

docs:
	mdbook build

combine-docs:
	./scripts/combine-docs.sh

test:
	cargo test --workspace

check:
	./scripts/check.sh
