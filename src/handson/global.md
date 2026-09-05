# 最小のスケジューラを動かす

最初の scheduler は、実行可能になったタスクを組み込みのグローバル DSQ へ入れる。
CPU ごとの優先度も、タスクごとの重みも持たない。

## checkpoint を作業領域へ戻す

```console
make restore STEP=01
```

参加者が編集するファイルは `lab/src/bpf/main.bpf.c` である。
完成状態は `checkpoints/step-01-global/` に残してある。

## callback を読む

`select_cpu` は、組み込みの CPU 選択処理へ判断を委ねる。

```c
s32 BPF_STRUCT_OPS(oreore_select_cpu, struct task_struct *p, s32 prev_cpu,
                   u64 wake_flags)
{
    bool is_idle = false;

    return scx_bpf_select_cpu_dfl(p, prev_cpu, wake_flags, &is_idle);
}
```

続く `enqueue` は、タスクを `SCX_DSQ_GLOBAL` へ入れる。

```c
void BPF_STRUCT_OPS(oreore_enqueue, struct task_struct *p, u64 enq_flags)
{
    scx_bpf_dsq_insert(p, SCX_DSQ_GLOBAL, slice_ns, enq_flags);
}
```

組み込みのグローバル DSQ は CPU が直接参照するため、この段階では `dispatch` を実装しなくてもタスクが動く。

## ビルドする

```console
make build STEP=lab
```

Mac 上で clang を実行しているわけではない。
Makefile は Multipass VM に入り、マウントした同じソースを clang 19 と Cargo でビルドする。

## ロードする

一つ目の端末で scheduler を起動する。

```console
make run STEP=lab MODE=partial
```

別の端末で状態を確認する。

```console
make vm-shell
cat /sys/kernel/sched_ext/state
cat /sys/kernel/sched_ext/root/ops
```

`state` が `enabled`、`ops` が `oreore` で始まる名前ならロードできている。
scx_utils が ops 名にバージョンとターゲット情報を自動付加するため、正確な文字列は `oreore_0.1.0_aarch64_unknown_linux_gnu` のようになる。
最初の端末で `Ctrl+C` を押すと scheduler が外れ、対象タスクは通常の scheduler に戻る。

