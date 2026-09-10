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

#define TEAM_A_DSQ 0
#define TEAM_B_DSQ 1

/* Each CPU remembers which shared DSQ to try first next time. */
struct {
	__uint(type, BPF_MAP_TYPE_PERCPU_ARRAY);
	__uint(max_entries, 1);
	__type(key, u32);
	__type(value, u32);
} dispatch_turn SEC(".maps");

s32 BPF_STRUCT_OPS(oreore_select_cpu, struct task_struct *p, s32 prev_cpu,
		   u64 wake_flags)
{
	bool is_idle = false;

	return scx_bpf_select_cpu_dfl(p, prev_cpu, wake_flags, &is_idle);
}

void BPF_STRUCT_OPS(oreore_enqueue, struct task_struct *p, u64 enq_flags)
{
	u64 dsq = bpf_strncmp(p->comm, 6, "team_a") == 0 ? TEAM_A_DSQ : TEAM_B_DSQ;

	scx_bpf_dsq_insert(p, dsq, slice_ns, enq_flags);
}

void BPF_STRUCT_OPS(oreore_dispatch, s32 cpu, struct task_struct *prev)
{
	u32 key = 0;
	u32 *turn = bpf_map_lookup_elem(&dispatch_turn, &key);
	u64 dsq;

	if (!turn)
		return;

	dsq = *turn;
	if (!scx_bpf_dsq_move_to_local(dsq, 0)) {
		dsq ^= 1;
		if (!scx_bpf_dsq_move_to_local(dsq, 0))
			return;
	}
	*turn = dsq ^ 1;
}

s32 BPF_STRUCT_OPS_SLEEPABLE(oreore_init)
{
	s32 err;

	err = scx_bpf_create_dsq(TEAM_A_DSQ, -1);
	if (err)
		return err;
	return scx_bpf_create_dsq(TEAM_B_DSQ, -1);
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
