// SPDX-License-Identifier: GPL-2.0-only
/*
 * Based on tools/sched_ext/scx_simple.bpf.c from Linux v6.18.49.
 * Copyright (c) 2022 Meta Platforms, Inc. and affiliates.
 * Copyright (c) 2022 Tejun Heo <tj@kernel.org>
 * Copyright (c) 2022 David Vernet <dvernet@meta.com>
 */
#include <scx/common.bpf.h>

char _license[] SEC("license") = "GPL";

const volatile u64 slice_ns = 20000000ULL;  /* 20 ms, kernel default */

UEI_DEFINE(uei);

s32 BPF_STRUCT_OPS(oreore_select_cpu, struct task_struct *p, s32 prev_cpu,
		   u64 wake_flags)
{
	bool is_idle = false;

	return scx_bpf_select_cpu_dfl(p, prev_cpu, wake_flags, &is_idle);
}

void BPF_STRUCT_OPS(oreore_enqueue, struct task_struct *p, u64 enq_flags)
{
	scx_bpf_dsq_insert(p, SCX_DSQ_GLOBAL, slice_ns, enq_flags);
}

void BPF_STRUCT_OPS(oreore_exit, struct scx_exit_info *ei)
{
	UEI_RECORD(uei, ei);
}

SCX_OPS_DEFINE(oreore_ops,
	       .select_cpu = (void *)oreore_select_cpu,
	       .enqueue    = (void *)oreore_enqueue,
	       .exit       = (void *)oreore_exit,
	       .timeout_ms = 5000,
	       .name       = "oreore");

