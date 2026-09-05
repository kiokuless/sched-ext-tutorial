// SPDX-License-Identifier: GPL-2.0-only
/*
 * Based on tools/sched_ext/scx_simple.bpf.c from Linux v6.18.49.
 * Copyright (c) 2022 Meta Platforms, Inc. and affiliates.
 * Copyright (c) 2022 Tejun Heo <tj@kernel.org>
 * Copyright (c) 2022 David Vernet <dvernet@meta.com>
 */
#include <scx/common.bpf.h>

char _license[] SEC("license") = "GPL";

const volatile u64 slice_ns = 10000000ULL;  /* 10 milliseconds */

UEI_DEFINE(uei);

#define SHARED_DSQ 0

s32 BPF_STRUCT_OPS(oreore_select_cpu, struct task_struct *p, s32 prev_cpu,
		   u64 wake_flags)
{
	bool is_idle = false;
	s32 cpu;

	cpu = scx_bpf_select_cpu_dfl(p, prev_cpu, wake_flags, &is_idle);
	if (is_idle)
		scx_bpf_dsq_insert(p, SCX_DSQ_LOCAL, slice_ns, 0);

	return cpu;
}

void BPF_STRUCT_OPS(oreore_enqueue, struct task_struct *p, u64 enq_flags)
{
	scx_bpf_dsq_insert(p, SHARED_DSQ, slice_ns, enq_flags);
}

void BPF_STRUCT_OPS(oreore_dispatch, s32 cpu, struct task_struct *prev)
{
	scx_bpf_dsq_move_to_local(SHARED_DSQ, 0);
}

s32 BPF_STRUCT_OPS_SLEEPABLE(oreore_init)
{
	return scx_bpf_create_dsq(SHARED_DSQ, -1);
}

void BPF_STRUCT_OPS(oreore_exit, struct scx_exit_info *ei)
{
	UEI_RECORD(uei, ei);
}

SCX_OPS_DEFINE(oreore_ops,
	       .select_cpu = (void *)oreore_select_cpu,
	       .enqueue    = (void *)oreore_enqueue,
	       .dispatch   = (void *)oreore_dispatch,
	       .init       = (void *)oreore_init,
	       .exit       = (void *)oreore_exit,
	       .timeout_ms = 5000,
	       .name       = "oreore");
