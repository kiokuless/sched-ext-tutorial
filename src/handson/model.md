# 最初の main.bpf.c を読む

前章では、`lab/src/bpf/main.bpf.c` の `slice_ns` を変えて、sleep の表示間隔が変わるところを確かめた。
このファイルには、その時間をタスクへ割り当てる処理や、実行待ちの列へタスクを入れる処理が書かれている。
Mac 側のエディタで開き、コードと実際の動きを対応させて読んでみよう。
前章の最後まで進めた状態は、`checkpoints/step-03-short-slice/src/bpf/main.bpf.c` と同じである。

## callback をカーネルへ登録する

`main.bpf.c` は、Linux カーネルから呼ばれる BPF プログラムである。
カーネルは、アプリケーションの各スレッドをタスクとして扱い、CPU を割り当てる。
このファイルには、その割り当てを決めるための処理が書かれている。

この C ファイルには、処理の入口となる `main()` がない。
代わりに、カーネルが必要な場面で呼ぶ関数を定義している。
このように、呼び出してもらうために登録する関数を **callback** と呼ぶ。

ファイル末尾の `SCX_OPS_DEFINE` で、カーネルが呼ぶ役割と、このファイルで定義した関数を対応付けている。

```c
SCX_OPS_DEFINE(oreore_ops,
	       .select_cpu = (void *)oreore_select_cpu,
	       .enqueue    = (void *)oreore_enqueue,
	       .exit       = (void *)oreore_exit,
	       .timeout_ms = 5000,
	       .name       = "oreore");
```

`SCX_OPS_DEFINE` は、関数と設定をまとめた **`sched_ext_ops`** という構造体を定義するマクロである。
ここでは、そのまとまりに `oreore_ops` という名前を付けている。
たとえば `.enqueue = (void *)oreore_enqueue` は、「タスクを列へ入れる場面では `oreore_enqueue` を呼ぶ」という対応を指定している。この対応付けをカーネルへ読み込んで有効にするのが、Rust の loader（`lab/src/main.rs`）である。

関数に続く `timeout_ms = 5000` は、実行可能なのに長く動けないタスクを検出するためのタイムアウトを5秒に設定している。
タイムアウトによる監視は、発展編の[壊して、戻る](../advanced/watchdog.md)で使う。

ここで登録した三つの関数は、それぞれ次の場面で呼ばれる。

| 関数 | 呼ばれる場面の例 | このコードがすること |
|---|---|---|
| `oreore_select_cpu` | 待機していたタスクが実行可能になったときや、新しいタスクを初めて動かすとき | CPU の候補を返す |
| `oreore_enqueue` | タスクが待機から復帰したときや、スライスを使い切って別のタスクと交代するとき | 実行待ちの列に入れる |
| `oreore_exit` | スケジューラが終了する時 | 終了理由を記録する |

## oreore_select_cpu で CPU の候補を選ぶ

待機していたタスクが再び実行可能になることを **wakeup** と呼ぶ。
wakeup したタスクが使える CPU が複数あれば、カーネルは `oreore_select_cpu` を呼び、実行先の候補を求める。
新しく作られたタスクを初めて動かすときにも、この CPU 選択が行われる。

```c
s32 BPF_STRUCT_OPS(oreore_select_cpu, struct task_struct *p, s32 prev_cpu,
		   u64 wake_flags)
{
	bool is_idle = false;

	return scx_bpf_select_cpu_dfl(p, prev_cpu, wake_flags, &is_idle);
}
```

`SCX_OPS_DEFINE` で登録する callback は、カーネルから呼び出せる BPF プログラムとして定義する。
`BPF_STRUCT_OPS` は、そのために必要な定型的な記述をまとめ、関数定義を簡潔に書けるようにするマクロである。[^callback-definition]
最初の引数が関数名で、ここでは `oreore_select_cpu` という関数を定義している。

冒頭の `SCX_OPS_DEFINE` にある `.select_cpu = (void *)oreore_select_cpu` は、定義した関数を CPU 選択の callback として登録する指定である。
カーネルがこの関数を呼ぶとき、対象タスクや前回動いていた CPU などの情報を引数で渡す。

今の実装では、その情報を `scx_bpf_select_cpu_dfl()` に渡し、CPU 選びを任せている。
これは、タスクが使える CPU の中から空いているものを探す、カーネルが用意した関数である。
`return` は、この関数が選んだ CPU 番号をそのままカーネルへ返す。
たとえば CPU 1 が選ばれれば、`oreore_select_cpu` も `1` を返す。

このコードの役割は、CPU の候補を返すところまでである。
タスクを実行待ちの列へ入れる処理は、その後の `oreore_enqueue` が担当する。

使える CPU が一つだけなら、候補を選ぶ必要がないため、この callback は省略される。
前章の `taskset -c 0` は、この場合に当たる。[^cpu-selection]

`is_idle` は、選ばれた CPU が空いている状態（**idle**）かどうかを受け取る変数だが、今のコードではその値を使っていない。
次章の[偶数用と奇数用に振り分ける](./shared-dsq.md#oreore_enqueue-で偶数用と奇数用に振り分ける)でも、この関数は CPU の候補を返す役割のまま使う。
タスクを分類する処理は、後から呼ばれる `enqueue` に加える。
今は「`oreore_select_cpu` はカーネルから呼ばれる関数で、CPU 選びを既定の処理に任せ、その番号を返す」と押さえておけばよい。

## oreore_enqueue で実行待ちの列に入れる

実行可能になったタスクは、CPU の順番を待つために待ち行列へ入る。
このコードでは、wakeup 後にカーネルが `oreore_enqueue` を呼び、そのタスクを引数の `p` に渡す。
CPU が一つに固定され、`select_cpu` が省略された場合も、`enqueue` は呼ばれる。

また、実行中のタスクがスライスを使い切り、ほかのタスクと交代する際にも呼ばれる。
交代したタスクは引き続き実行可能なので、再び列に入って次の順番を待つ。
このように、実行を待つタスクを列へ入れる処理が **`enqueue`** である。

I/O などの待機に入るタスクは、待ちが解消されるまで実行できない。
そのため、待機に入る時点では実行待ちの列に戻さず、wakeup したときに `enqueue` で戻す。

```c
void BPF_STRUCT_OPS(oreore_enqueue, struct task_struct *p, u64 enq_flags)
{
	scx_bpf_dsq_insert(p, SCX_DSQ_GLOBAL, slice_ns, enq_flags);
}
```

`p` は列に入れるタスクを指し、`enq_flags` は投入時の条件を表す。
この関数は結果の値を返さないため、戻り値の型は `void` になっている。

タスクを CPU へ渡すために使う待ち行列を **dispatch queue（DSQ）** と呼ぶ。
`scx_bpf_dsq_insert()` は、指定した DSQ へタスクを入れる関数である。
この一行では、四つの引数で次の内容を指定している。
`slice_ns` は前章で変更した値で、現在は 10 ミリ秒である。

| 引数 | このコードでの指定 |
|---|---|
| `p` | カーネルから渡されたタスクを入れる |
| `SCX_DSQ_GLOBAL` | 組み込みのグローバル DSQ に入れる |
| `slice_ns` | 今回の CPU 時間として 10 ミリ秒を割り当てる |
| `enq_flags` | カーネルから渡された投入条件をそのまま使う |

**グローバル DSQ** は、カーネルが用意した、複数の CPU で共有する待ち行列である。
このコードは、実行を待つタスクをそこへ入れ、入った順に取り出す **FIFO** という並べ方を使っている。
タスクを入れる時点でスライスも指定するため、前章で変えた `slice_ns` がここからタスクへ渡る。

### 列から取り出すのはカーネル

このファイルには、グローバル DSQ からタスクを取り出す関数がない。
そこはカーネルが担当している。

各 CPU には、その CPU が次に実行するタスクを置く **ローカル DSQ** がある。
それが空なら、カーネルはグローバル DSQ から、その CPU で実行できるタスクをローカル DSQ へ移す。
CPU はローカル DSQ からタスクを取り出して実行する。

<figure class="technical-figure">
<div class="diagram-scroll" tabindex="0" role="region" aria-label="グローバル DSQ を使うタスクの循環（横スクロール可能）">
<img src="../images/dsq-global-cycle.svg" alt="待機から復帰したタスクは select_cpu と enqueue を経てグローバル DSQ に入る。カーネルがタスク A を CPU 1 のローカル DSQ へ移し、CPU 1 が実行する。スライスを使い切って交代し、まだ実行可能なら、select_cpu を通らず enqueue でグローバル DSQ へ戻る。">
</div>
</figure>

グローバル DSQ は複数の CPU が参照するため、実際に取り出す CPU が、先ほどの `select_cpu` の候補と同じとは限らない。
図の CPU 1 は今回の実行先の一例であり、再投入後には別の CPU が取り出すこともある。

図の右側の矢印は、スライスを使い切って交代したタスク A が、引き続き実行可能なまま再投入される流れである。
この場合は `oreore_select_cpu` を通らず、`oreore_enqueue` がグローバル DSQ へ戻す。

## oreore_exit で終了理由を記録する

カーネルは、BPF スケジューラを取り外す際に `oreore_exit` を呼ぶ。
loader の停止によって接続が解放された場合も、異常を検出してスケジューラを停止する場合も、この関数で終了理由を受け取る。

これはスケジューラ全体の終了に対する通知であり、個々のタスクの終了通知ではない。
引数の `ei` には、スケジューラが終了した理由が入っている。

```c
void BPF_STRUCT_OPS(oreore_exit, struct scx_exit_info *ei)
{
	UEI_RECORD(uei, ei);
}
```

ファイル先頭の `UEI_DEFINE(uei);` は、終了理由を保存する場所を `uei` という名前で用意する。
`UEI_RECORD` は、そこへ `ei` の内容を書き込む。
Rust 側の loader がこの記録を読み、端末へ表示する。
`Ctrl+C` で停止したときに出た次の行も、この仕組みによるものである。

```text
EXIT: unregistered from user space
```

[^callback-definition]: マクロの定義は、scx v1.1.3 の [`BPF_STRUCT_OPS`](https://github.com/sched-ext/scx/blob/v1.1.3/scheds/include/scx/common.bpf.h#L227-L229) と [`SCX_OPS_DEFINE`](https://github.com/sched-ext/scx/blob/v1.1.3/scheds/include/scx/compat.bpf.h#L477-L481) で確認できる。
[^cpu-selection]: CPU 選択の処理は、Linux 7.0 の [`scx_bpf_select_cpu_dfl()`](https://github.com/torvalds/linux/blob/v7.0/kernel/sched/ext_idle.c#L909-L941) と、CPU を一つに固定した場合の [`select_task_rq()`](https://github.com/torvalds/linux/blob/v7.0/kernel/sched/core.c#L3313-L3337) で確認できる。
