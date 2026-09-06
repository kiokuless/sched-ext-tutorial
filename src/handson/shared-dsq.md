# 自分の DSQ を作る

前章のスケジューラは、タスクをグローバル DSQ へ入れた後の取り出しをカーネルに任せていた。
もし待ち行列を二つに分け、一方を優先して取り出したくなったら、どこにその判断を書けばよいだろうか。
独自 DSQ を作ると、`dispatch` で取り出すキューを選べるようになる。

まず共有の独自 DSQ を一つだけ作り、FIFO のまま受け渡しの経路を変更する。
DSQ 自体はカーネルが提供するが、作成するタイミングと、そこからタスクを取り出す処理は自分で指定する。
この段階では性能の改善を狙わず、タスクが CPU に届くまでをコードで追えることを目標にする。

## 前章のコードから変更する

編集するファイルは `lab/src/bpf/main.bpf.c` である。
前章から続けている場合は、そのまま変更を加える。
途中から始める場合だけ、次のコマンドで前章の完成状態を復元する。
`make restore` は lab の BPF ファイルを上書きするので、残したい変更は先に保存しておく。

```console
make restore STEP=01
```

## 共有 DSQ を作成する

独自 DSQ は、タスクを入れる前に作成しておく必要がある。
`UEI_DEFINE(uei);` の後に DSQ の ID を定義し、`exit` callback の前に `init` を追加する。

```c
#define SHARED_DSQ 0

s32 BPF_STRUCT_OPS_SLEEPABLE(oreore_init)
{
    return scx_bpf_create_dsq(SHARED_DSQ, -1);
}
```

独自 DSQ の ID は `u64` のうち `2^63` 未満から選ぶ。
ここでは 0 を `SHARED_DSQ` と名付けた。
上位ビットを使う領域は、`SCX_DSQ_GLOBAL` などの組み込み ID に予約されている。

`BPF_STRUCT_OPS_SLEEPABLE` は、処理の途中で待機できる実行コンテキストの callback を定義する。
メモリ確保を伴う DSQ の作成は、この `init` に置く。
`scx_bpf_create_dsq()` の第2引数はメモリの割り当て先となる NUMA node で、-1 は特定の node を指定しない。

## 入れる先と取り出す処理を変更する

`enqueue` の投入先を `SCX_DSQ_GLOBAL` から `SHARED_DSQ` に変更する。

```c
void BPF_STRUCT_OPS(oreore_enqueue, struct task_struct *p, u64 enq_flags)
{
    scx_bpf_dsq_insert(p, SHARED_DSQ, slice_ns, enq_flags);
}
```

投入先を変えただけでは、このキューからタスクを取り出す処理がない。
続けて `dispatch` を追加し、共有 DSQ から呼び出し元 CPU のローカル DSQ へ、実行可能なタスクを移す。

```c
void BPF_STRUCT_OPS(oreore_dispatch, s32 cpu, struct task_struct *prev)
{
    scx_bpf_dsq_move_to_local(SHARED_DSQ, 0);
}
```

CPU はローカル DSQ とグローバル DSQ に次のタスクが見つからないと、`dispatch` を呼び出す。
この実装では共有 DSQ から一つ移すだけだが、複数の独自 DSQ を持てば、ここで取り出す順番を選べる。

最後に、ファイル末尾の `SCX_OPS_DEFINE` に次の二行を追加する。
関数を書くだけでは callback として登録されない。

```c
.dispatch   = (void *)oreore_dispatch,
.init       = (void *)oreore_init,
```

この二行まで揃えてからビルドし、ロードする。

```console
make build STEP=lab
make run STEP=lab MODE=partial
```

別の端末から、前章と同じ方法で `state` が `enabled`、`root/ops` が `oreore` で始まることを確かめる。
確認後はロードした端末で `Ctrl+C` を押し、`state` が `disabled` に戻ることも確認する。

## 空いている CPU へ直接渡す

共有 DSQ を経由する経路ができた。
ただ、起床時に空いている CPU が見つかるなら、いったん共有 DSQ へ入れる必要はない。
`select_cpu` を次の内容に置き換える。

```c
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
```

`is_idle` が真なら、戻り値の CPU のローカル DSQ へ直接投入する。
この場合は `enqueue` が省略されるので、同じタスクが共有 DSQ にも入ることはない。
空いている CPU が見つからなければ、先ほど作った `enqueue` と `dispatch` の経路を通る。

もう一度ビルドとロードを確認し、終了してから、タスクを実際に流してみる。
次のコマンドは scheduler のロードから負荷生成器の起動、停止までを行う。

```console
make bench CASE=step STEP=lab
```

15 標本と集計結果が出て終了することを確認する。
数値の読み方は[長いスライスの実験](./long-slice.md#測っている遅れ)で扱う。
完成状態との違いは、ホスト側で次のコマンドを使って確認できる。

```console
diff -u checkpoints/step-02-shared-dsq/src/bpf/main.bpf.c lab/src/bpf/main.bpf.c
```

空白や関数の配置が違っていてもよい。
DSQ の ID、三つの scheduling callback、`init`、ops への登録を照合する。

## 経路を確かめる

空いている CPU がある場合と、すべて使用中の場合について、タスクが通る callback と DSQ を順に書いてみる。
それぞれで `enqueue` が呼ばれるかも答える。

<details>
<summary>解答と理由</summary>

空いている CPU を見つけた場合は、`select_cpu` からその CPU のローカル DSQ へ直接投入し、`enqueue` を省略する。
見つからない場合は、`enqueue` が共有 DSQ へ入れ、後で `dispatch` がローカル DSQ へ移す。
どちらの経路でも、CPU が実行するタスクを取り出す先はローカル DSQ である。

</details>

DSQ の制約と直接投入の条件は、Linux 7.0 の [Scheduling Cycle](https://docs.kernel.org/7.0/scheduler/sched-ext.html#scheduling-cycle) に記載されている。
