# Invoke scripts via Bash: Windows shares do not preserve executable bits.
SHELL := /bin/bash

VM_NAME ?= sched-ext-lab
STEP ?= 01
MODE ?= partial
CASE ?= step
RACE_CPU ?= 0
RACE_CPU_SECONDS ?= 12
TEAM_A_MEMBERS ?= 3

.PHONY: vm-up vm-mount vm-bootstrap vm-shell vm-stop doctor build run bench race team-race reset restore verify-checkpoints docs combine-docs test check

vm-up:
	VM_NAME="$(VM_NAME)" bash ./scripts/vm-up.sh

vm-mount:
	VM_NAME="$(VM_NAME)" bash ./scripts/vm-mount.sh

vm-bootstrap:
	VM_NAME="$(VM_NAME)" bash ./scripts/vm-bootstrap.sh

vm-shell:
	multipass shell "$(VM_NAME)"

vm-stop:
	multipass stop "$(VM_NAME)"

doctor:
	VM_NAME="$(VM_NAME)" bash ./scripts/vm-exec.sh bash ./scripts/guest/doctor.sh

build:
	VM_NAME="$(VM_NAME)" bash ./scripts/vm-exec.sh bash ./scripts/guest/build-step.sh "$(STEP)"

run:
	VM_NAME="$(VM_NAME)" bash ./scripts/vm-exec.sh bash ./scripts/guest/run-step.sh "$(STEP)" "$(MODE)"

bench:
	VM_NAME="$(VM_NAME)" bash ./scripts/vm-exec.sh bash ./scripts/guest/bench.sh "$(CASE)" "$(STEP)"

race:
	VM_NAME="$(VM_NAME)" bash ./scripts/vm-exec.sh bash ./scripts/guest/race.sh "$(STEP)" "$(RACE_CPU)" "$(RACE_CPU_SECONDS)"

team-race:
	VM_NAME="$(VM_NAME)" bash ./scripts/vm-exec.sh bash ./scripts/guest/team-race.sh "$(STEP)" "$(RACE_CPU)" "$(TEAM_A_MEMBERS)"

reset:
	VM_NAME="$(VM_NAME)" bash ./scripts/vm-exec.sh bash ./scripts/guest/reset.sh

restore:
	bash ./scripts/restore-step.sh "$(STEP)"

verify-checkpoints:
	VM_NAME="$(VM_NAME)" bash ./scripts/vm-exec.sh bash ./scripts/guest/verify-checkpoints.sh

docs:
	mdbook build

combine-docs:
	bash ./scripts/combine-docs.sh

test:
	cargo test --workspace

check:
	bash ./scripts/check.sh
