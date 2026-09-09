# 自分の待ち行列から取り出す

前章のスケジューラは、すべてのタスクを一つのグローバル DSQ に入れていた。
今度は、プロセス番号が偶数なら DSQ 0、奇数なら DSQ 1 に分け、二つの列へ交互に順番を回す。
同じ 10 ミリ秒のスライスでも、誰と同じ列に入るかで CPU 時間の配分が変わる。

## 待ち行列を分ける理由

一つの FIFO に四つのタスクが並んでいれば、それぞれに順番が回る。
三つと一つの二列に分け、列を交互に選ぶとどうなるだろうか。
三つのタスクは自分たちの列に来た順番を分け合い、もう一方の一つは、その列の順番を独占できる。

このように分類と取り出し方を指定したいときは、BPF 側からカーネルへ新しい待ち行列の作成を依頼できる。
こうして作る待ち行列を **独自 DSQ** と呼ぶ。
キューのデータ構造や出し入れの仕組みはカーネルが提供し、自作コードで「どこへ入れるか」と「どの列から取り出すか」を決める。

今回は、プロセス番号（**PID**）の偶奇で振り分ける。
偶数と奇数は処理内容とは関係しないが、番号を見れば投入先を予想できる。
後から応答用と計算用などに分ける場合も、分類する条件を置く場所は同じである。

<figure class="technical-figure">
<div class="diagram-scroll" tabindex="0" role="region" aria-label="一つの FIFO と偶奇で分けた二つの DSQ の比較（横スクロール可能）">
<img src="../images/dsq-policy-choice.svg" alt="同じ四つの単一スレッドのプロセスを比較する。一つの FIFO なら四つへ順番が回る。偶数用に三つ、奇数用に一つを入れて列を交互に選ぶと、奇数側の一つには偶数側の各プロセスより頻繁に順番が回る。">
</div>
<figcaption>四つとも CPU を使い続け、同じスライスを使い切る場合の比較。CPU は一つに揃える。</figcaption>
</figure>

DSQ 0 と DSQ 1 は、どちらも複数の CPU から取り出せる **共有 DSQ** として使う。
0 と 1 は待ち行列の ID であり、実行先の CPU 番号を指定する値ではない。
列の中は FIFO のままにし、列を選ぶ順番を自作する。

## 二つの DSQ で使う callback を登録する

独自 DSQ の作成と、ローカル DSQ への受け渡しも、カーネルから呼ばれる callback に書く。
スケジューラを初期化する **`init`** と、CPU が次に実行するタスクを求めたときに呼ばれる **`dispatch`** を加える。

編集先は `lab/src/bpf/main.bpf.c` である。
スライスが 10 ミリ秒の状態から始める。
loader が動いていれば、先に終了する。
途中から始める場合は、残したい変更を保存してから `make restore STEP=03` で揃える。

ファイル末尾の `SCX_OPS_DEFINE` に `.dispatch` と `.init` の二行を加え、次の形にする。

```c
SCX_OPS_DEFINE(oreore_ops,
	       .select_cpu = (void *)oreore_select_cpu,
	       .enqueue    = (void *)oreore_enqueue,
	       .dispatch   = (void *)oreore_dispatch,
	       .init       = (void *)oreore_init,
	       .exit       = (void *)oreore_exit,
	       .timeout_ms = 5000,
	       .name       = "oreore");
```

`.init` に登録した `oreore_init` で二つの DSQ を作り、`.dispatch` に登録した `oreore_dispatch` で取り出す列を選ぶ。
変更後の callback の役割は、次のようになる。

| callback | 呼ばれる場面の例 | 今回のコードがすること |
|---|---|---|
| `init` | スケジューラを初期化するとき | 偶数用と奇数用の DSQ を作成する |
| `select_cpu` | 待機から復帰したタスクなどの CPU 候補を選ぶとき | 前章と同じく CPU の候補を返す |
| `enqueue` | タスクを実行待ちの列へ入れるとき | PID の偶奇で投入先を選ぶ |
| `dispatch` | ローカル DSQ とグローバル DSQ に実行できるタスクが見つからないとき | 二つの列を交互に選び、ローカル DSQ へ移す |
| `exit` | スケジューラが終了するとき | 前章と同じく終了理由を記録する |

新しく登録した二つの関数は、まだ定義していない。
ロードは、その定義と `oreore_enqueue` の変更まで揃えてから行う。

## oreore_init で二つの DSQ を作成する

カーネルはスケジューラの初期化時に `oreore_init` を呼ぶ。
この中で、タスクの投入先となる二つの DSQ を作っておく。
まず、作成と投入で同じ待ち行列を指定できるよう、ID に名前を付ける。
`UEI_DEFINE(uei);` の後に次を追加する。

```c
#define EVEN_DSQ 0
#define ODD_DSQ 1
```

続いて、`oreore_exit` の前に次の関数を追加する。

```c
s32 BPF_STRUCT_OPS_SLEEPABLE(oreore_init)
{
	s32 err;

	err = scx_bpf_create_dsq(EVEN_DSQ, -1);
	if (err)
		return err;
	return scx_bpf_create_dsq(ODD_DSQ, -1);
}
```

`scx_bpf_create_dsq()` は、指定した ID の待ち行列をカーネルに作成させる関数である。
成功すると 0、失敗すると負のエラー値を返す。
最初の作成が失敗したら、その値をカーネルへ返して初期化を終え、成功した場合にだけ二つ目を作る。

<details>
<summary>DSQ の ID と作成時の指定</summary>

独自 DSQ の ID は `u64` のうち `2^63` 未満から選べる。
上位ビットを使う領域は、`SCX_DSQ_GLOBAL` などの組み込み ID に予約されている。
ここでは 0 を `EVEN_DSQ`、1 を `ODD_DSQ` と名付けた。

`BPF_STRUCT_OPS_SLEEPABLE` は、途中で待機できる実行コンテキストの callback を定義する。
メモリ確保を伴う DSQ の作成は、この `init` に置く。
`scx_bpf_create_dsq()` の第2引数はメモリの割り当て先となる NUMA node で、-1 は特定の node を指定しない。

</details>

## oreore_enqueue で偶数用と奇数用に振り分ける

実行待ちのタスクを列へ入れる役割は、前章と同じ `oreore_enqueue` が担当する。
投入先を決めるために、渡されたタスクのプロセス番号を読む。

```c
void BPF_STRUCT_OPS(oreore_enqueue, struct task_struct *p, u64 enq_flags)
{
	u64 dsq = (p->tgid % 2 == 0) ? EVEN_DSQ : ODD_DSQ;

	scx_bpf_dsq_insert(p, dsq, slice_ns, enq_flags);
}
```

`p->tgid` は、そのタスクが属するプロセスの番号である。
Linux ではスケジューラが扱うタスクはスレッドに対応し、`p->pid` はスレッド自身の番号を表す。
今回はプロセスごとに分類するので、同じプロセスに属するスレッドを同じ列へ入れる `tgid` を使う。[^task-id]

`% 2` は 2 で割った余りを求める演算である。
余りが 0 なら偶数用、それ以外なら奇数用の ID を `dsq` に入れ、`scx_bpf_dsq_insert()` の第2引数に渡す。
`slice_ns` と `enq_flags` は前章のままなので、変わるのは投入先である。

`oreore_select_cpu` は CPU の候補を返す前章の実装を使う。
ここでローカル DSQ へ直接投入すると `enqueue` が省略されるため、偶奇の振り分けを通らない。
この実験では、idle CPU が見つかった場合も `enqueue` に進める。[^scheduling-cycle]

## oreore_dispatch で二つの列を交互に選ぶ

CPU のローカル DSQ とグローバル DSQ に実行できるタスクが見つからないと、カーネルは `oreore_dispatch` を呼ぶ。
毎回偶数用から取り出すと、偶数用が空にならない間、奇数用を選べない。
交互に選ぶには、次にどちらから取り出すかを記録しておく必要がある。

### CPU ごとに次の順番を記録する

callback の呼び出しをまたいで値を保持するため、キーと値を保存できる **BPF map** を使う。
今回保存するのは「次に先に試す DSQ の ID」である。
`EVEN_DSQ` と `ODD_DSQ` の定義の後に、次を追加する。

```c
struct {
	__uint(type, BPF_MAP_TYPE_PERCPU_ARRAY);
	__uint(max_entries, 1);
	__type(key, u32);
	__type(value, u32);
} dispatch_turn SEC(".maps");
```

`BPF_MAP_TYPE_PERCPU_ARRAY` は、CPU ごとに別の値を持つ配列である。
要素数は一つで、キー 0 の値を各 CPU が一つずつ持つ。
このキー 0 も CPU 番号ではない。
値は作成時に 0 で初期化されるので、各 CPU は偶数用の DSQ から試し始める。[^per-cpu-map]

CPU 0 が順番を更新しても、CPU 1 の順番は変わらない。
この実装の「交互」は、各 CPU が取り出す順番を指す。
実験では CPU を一つに揃え、その順番と配分を観察する。

### 取り出せた列の反対を次の候補にする

`oreore_enqueue` の後に次の関数を追加する。

```c
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
```

`bpf_map_lookup_elem()` は、呼び出し元 CPU が持つキー 0 の値へのポインタを返す。
`if (!turn)` は取得に失敗した場合の確認で、ポインタを使う前に置く。
`*turn` で読んだ ID の列から、まず取り出してみる。

`scx_bpf_dsq_move_to_local()` は、指定した DSQ から呼び出し元 CPU のローカル DSQ へタスクを移し、成功したかを返す。
列が空の場合や、その CPU で実行できるタスクが見つからない場合は、もう一方を試す。
`^ 1` は最下位のビットを反転する演算で、ここでは 0 と 1 を入れ替えるために使っている。

移動できたら、その列とは反対の ID を `*turn` に保存する。
両方に実行できるタスクがあれば 0、1、0、1 と選び、片方が空なら、タスクがある側から取り出せる。
CPU が最後にタスクを取り出す先は、前章と同じローカル DSQ である。

<figure class="technical-figure">
<div class="diagram-scroll" tabindex="0" role="region" aria-label="偶数用と奇数用の共有 DSQ を使うタスクの循環（横スクロール可能）">
<img src="../images/dsq-shared-cycle.svg" alt="init が偶数用の DSQ 0 と奇数用の DSQ 1 を作成する。待機から復帰したタスクは select_cpu を経て、enqueue が PID の偶奇で列へ入れる。dispatch は CPU ごとに二つの列を交互に選び、ローカル DSQ へ移す。スライスを使い切って交代しても実行可能なら、select_cpu を通らず enqueue で同じ偶奇の列へ戻る。">
</div>
<figcaption>DSQ 0 と DSQ 1 はどちらも各 CPU から取り出せる。図の CPU 1 は実行先の一例である。</figcaption>
</figure>

スライスを使い切って交代した後も実行可能なら、前章と同じく `enqueue` で列へ戻る。
この再投入では `select_cpu` を通らず、同じ PID の偶奇で再び分類される。

## 変更したスケジューラを動かす

`SCX_OPS_DEFINE` への登録と、DSQ の作成、投入、取り出しの処理が揃った。
端末1（Mac 側のリポジトリ直下）でロードする。

```console
make run STEP=lab MODE=partial
```

端末2から VM に入り、最初の起動確認と同じ周期タスクを動かす。

```console
make vm-shell
cat /sys/kernel/sched_ext/state
cat /sys/kernel/sched_ext/root/ops
sudo /var/cache/sched-ext-tutorial/target/workload/release/sched-ext-workload \
    periodic --samples 3 --sched-ext
```

`enabled` と `oreore` で始まる名前、三つの標本を確認する。
周期タスクは一つなので、二つの列へ交互に順番が回ることまでは、この出力では分からない。
ここでは、片方の列にしかタスクがなくても実行が進むことを確かめている。

確認したら、端末1で `Ctrl+C` を押す。
端末2で解除を確認し、Mac 側へ戻る。

```console
cat /sys/kernel/sched_ext/state
exit
```

## 偶数を三つ、奇数を一つ動かす

二つの列で人数を変え、各プロセスが受け取った CPU 時間を比較する。
実験用の補助スクリプトは、偶数 PID を三つ、奇数 PID を一つ揃え、すべてを CPU 0 で動かす。
各プロセスは単一スレッドで同じ計算を続け、スライスを使い切る。

まず、前章の一つの FIFO で測る。
Mac 側のリポジトリ直下で、スケジューラを停止した状態から実行する。

```console
make bench CASE=dsq STEP=03
```

続いて、変更した lab を同じ条件で測る。

```console
make bench CASE=dsq STEP=lab
```

このコマンドは指定したスケジューラを partial mode で起動し、準備ができた四つのプロセスを 10 秒間測定して、終了時にスケジューラも解除する。
完成例で比較する場合は `STEP=lab` を `STEP=04` に変える。
起動するたびに PID は変わるが、偶数三つと奇数一つという人数は揃える。
以前の実験で動かした `SCHED_EXT` のタスクが同じ CPU に残っている場合は、混入を検出して測定を中止する。
表示されたタスクを実行している端末で終了してから、測り直す。

出力の `cpu_ms` は測定区間に各プロセスが使った CPU 時間、`share_percent` は四つのプロセスの CPU 時間の合計に占める割合である。
CPU 時間は `/proc/<PID>/schedstat` の累積実行時間の差分から求める。[^cpu-runtime]
待っていた時間や、ほかのプロセスが使った時間は、この割合の分母に含めない。
末尾の `scheduler_state_after=disabled` で解除も確認する。

| 方針 | 偶数側の各プロセス | 奇数側の一つ | 同じ長さのスライスを交互に渡した場合の考え方 |
|---|---|---|---|
| 一つの FIFO | 約 25% | 約 25% | 四つで順番を分け合う |
| 二つの DSQ を交互に選ぶ | 約 16.7% | 約 50% | 各列に半分ずつ、偶数側は三つで分け合う |

これは配分の目安であり、実行中の割り込みや、ほかのタスクとの交代、VM の実行状況などによって実測値はずれる。
自分の出力では、奇数側の一つと、偶数側の各プロセスの割合を比べる。

2026年9月9日に教材 VM の CPU 0 で測ったところ、一つの FIFO では各プロセスが 24.9〜25.1% を受け取った。
二つの DSQ では偶数側がそれぞれ 16.6%、16.7%、16.7%、奇数側が 50.0% になった。
実行条件と出力は、[一つの FIFO の記録](../measurements/2026-09-09/dsq-global.txt)と[二つの DSQ の記録](../measurements/2026-09-09/dsq-parity.txt)に残している。

列へ同じ回数だけ順番を回しても、プロセスごとの CPU 時間が等しくなるとは限らない。
今回の四つなら、偶数側の各プロセスは三回に一回しか自分の列の先頭になれない。
独自 DSQ に分類と取り出しの規則を加えたことで、誰と順番を分け合うかも自作コードの方針になった。

## 完成例と照合する

Mac 側で次の差分を読む。

```console
diff -u checkpoints/step-04-shared-dsq/src/bpf/main.bpf.c lab/src/bpf/main.bpf.c
```

空白や関数の配置が違っていてもよい。
二つの DSQ の ID、`dispatch_turn`、`init`、`enqueue`、`dispatch`、ops への登録を照合する。
`select_cpu` は前章の、CPU の候補を返す実装のままである。

[^task-id]: Linux 7.0 の [`task_struct` と PID の定義](https://github.com/torvalds/linux/blob/v7.0/include/linux/sched.h)では、`pid` と `tgid` を区別している。
    ここでは教材 VM の PID 名前空間で動かし、コンテナ内の PID は扱わない。
[^per-cpu-map]: [BPF_MAP_TYPE_ARRAY and BPF_MAP_TYPE_PERCPU_ARRAY](https://docs.kernel.org/bpf/map_array.html) に、作成時のゼロ初期化と、呼び出し元 CPU の要素を読み書きする仕組みが記載されている。
[^scheduling-cycle]: 直接投入による `enqueue` の省略と、`dispatch` の呼び出し条件は Linux 7.0 の [Scheduling Cycle](https://docs.kernel.org/7.0/scheduler/sched-ext.html#scheduling-cycle) で確認できる。
[^cpu-runtime]: [Scheduler Statistics](https://docs.kernel.org/scheduler/sched-stats.html) に、`/proc/<PID>/schedstat` の先頭の値がナノ秒単位の CPU 実行時間であると記載されている。
