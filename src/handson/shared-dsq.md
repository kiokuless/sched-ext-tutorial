# 自分の DSQ を作る

組み込みのグローバル DSQ へ入れたタスクは、CPU が直接取り出していた。
自分で DSQ を作ると、そのキューからいつ、どの CPU へタスクを渡すかも callback の仕事になる。

```console
make restore STEP=02
```

## idle CPU への直接 dispatch

`select_cpu` が idle CPU を見つけた場合は、その CPU のローカル DSQ へ直接タスクを入れる。
待ち行列を一段飛ばせるため、空いている CPU があるのに共有 DSQ で待つ必要がなくなる。

```c
cpu = scx_bpf_select_cpu_dfl(p, prev_cpu, wake_flags, &is_idle);
if (is_idle)
    scx_bpf_dsq_insert(p, SCX_DSQ_LOCAL, slice_ns, 0);
```

## 共有 DSQ から CPU へ渡す

idle CPU へ直接渡せなかったタスクは、ID 0の共有 DSQ に入れる。

```c
#define SHARED_DSQ 0

void BPF_STRUCT_OPS(oreore_enqueue, struct task_struct *p, u64 enq_flags)
{
    scx_bpf_dsq_insert(p, SHARED_DSQ, slice_ns, enq_flags);
}
```

CPU が仕事を求めると `dispatch` が呼ばれる。
`scx_bpf_dsq_move_to_local()` は共有 DSQ の先頭を、呼び出し元 CPU のローカル DSQ へ移す。

```c
void BPF_STRUCT_OPS(oreore_dispatch, s32 cpu, struct task_struct *prev)
{
    scx_bpf_dsq_move_to_local(SHARED_DSQ, 0);
}
```

独自 DSQ は初期化時に作成する。

```c
s32 BPF_STRUCT_OPS_SLEEPABLE(oreore_init)
{
    return scx_bpf_create_dsq(SHARED_DSQ, -1);
}
```

`make build STEP=lab` と `make run STEP=lab MODE=partial` で動作を確認する。
詰まった場合は `checkpoints/step-02-shared-dsq/` と比較できる。

