# 最小のスケジューラを動かす

差し替える場所と載せ方が分かったので、最初の scheduler を動かす。
最初の scheduler は、実行可能になったタスクを組み込みのグローバル DSQ へ入れる。
CPU ごとの優先度も、タスクごとの重みも持たない。
まずこの最小構成をビルドし、ロードし、外すところまでを一周して、作業の形を掴む。

## checkpoint を作業領域へ戻す

```console
make restore STEP=01
```

参加者が読み、以降の章で編集していくファイルは `lab/src/bpf/main.bpf.c` である。
各章の完成状態は `checkpoints/step-01-global/` に残してあり、`make restore` はそのコードを lab へ戻すコマンドである。
以降の章でも、restore でその章の状態を再現できる。

## callback を読む

`select_cpu` は、起床したタスクを動かす CPU の候補を選ぶ入口である。
この実装は、判断を組み込みの CPU 選択処理へ委ねている。

```c
s32 BPF_STRUCT_OPS(oreore_select_cpu, struct task_struct *p, s32 prev_cpu,
                   u64 wake_flags)
{
    bool is_idle = false;

    return scx_bpf_select_cpu_dfl(p, prev_cpu, wake_flags, &is_idle);
}
```

`scx_bpf_select_cpu_dfl()` は、前回動いていた CPU（`prev_cpu`）を起点に、idle な CPU を優先して選ぶ組み込み処理である。
`is_idle` は「idle CPU を見つけられたか」を受け取る出力引数で、この章では使っていない。
使うのは次章である。

続く `enqueue` は、実行可能になったタスクを `SCX_DSQ_GLOBAL` へ入れる。

```c
void BPF_STRUCT_OPS(oreore_enqueue, struct task_struct *p, u64 enq_flags)
{
    scx_bpf_dsq_insert(p, SCX_DSQ_GLOBAL, slice_ns, enq_flags);
}
```

第3引数の `slice_ns` は、このタスクに渡すタイムスライスである。
前章で述べたとおり、スライスはタスクが待ち行列に入れられるときに渡される。

`slice_ns` は、ファイルの先頭で scheduler 全体の既定値として定義されている。

```c
const volatile u64 slice_ns = 20000000ULL;  /* 20 ms, kernel default */
```

`const volatile` は、BPF プログラムの設定値を置くときの定石である。
`const` にしないとコンパイラが読み出しを最適化で消すことがあり、`volatile` にしないと「実行中に変わらない」と決めつけられる。
実際の値は、前章の流れで述べた rodata 経由で、loader がロード前に書き換えられる。
この値を書き換える実験が、後の二つの章である。

ファイルの末尾では、実装した callback を `SCX_OPS_DEFINE` がひとつの ops 構造体にまとめ、名前と timeout を設定する。
`exit` は scheduler が外されるときに停止理由を記録する小さな callback で、今は読み飛ばしてよい。
watchdog の章で再び登場する。

## ビルドする

```console
make build STEP=lab
```

Mac 上で clang を実行しているわけではない。
Makefile は Multipass VM に入り、マウントした同じソースを clang 19 と Cargo でビルドする。
前章で VM を用意したのは、このビルドのためである。

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

<!-- 初回の成功判定を明確にするため、state と ops の出力例をここに載せるとよい -->

最後に、scheduler を外す。
最初の端末で `Ctrl+C` を押すと loader が終了し、scheduler が外れ、対象タスクは通常の scheduler に戻る。
前章の流れの最後の行、loader の生存期間だけ scheduler が有効、がここで確認できたことになる。
以降の章では、この一連の流れを、コードの中身だけ変えながら繰り返す。
