# `sched_ext` が変えるもの

実行可能なタスクが一つしかなければ、選択はほとんど必要ない。
問題になるのは、複数のタスクが同時に CPU を欲しがったときだ。
CPU の割り当てを決める scheduler は、そのとき少なくとも次の四つの問いに答える必要がある。

- **誰を動かすか**：待っているタスクのうち、どれを先に実行するか
- **どこで動かすか**：どの CPU を候補にするか
- **いつ渡すか**：実行可能になったタスクを、いつ CPU 側へ送り出すか
- **どれだけ動かすか**：一度 CPU を得たタスクに、どれだけ連続して実行させるか

この四つは独立しているように見えるが、実際には互いに影響する。
たとえば、同じタスクを長く動かせば切り替え回数は減るが、その間に起きた別のタスクは待つことになる。
逆に、頻繁に選び直せば待ち時間を短くできる一方、切り替えの回数は増える。

`sched_ext` では、カーネルがタスクを扱う判断点で BPF プログラムを呼び出す。
この BPF プログラムが実装する入口の集合を **`sched_ext_ops`** と呼ぶ。

今回使う callback は三つである。

- **`select_cpu`**：起床したタスクを動かす CPU の候補を選ぶ
- **`enqueue`**：実行可能なタスクを待ち行列へ入れる
- **`dispatch`**：待ち行列からタスクを CPU のローカルキューへ移す

三つの callback は、CPU の候補選択、タスクの保管、CPU への受け渡しを分担する。
`select_cpu` が返す CPU は候補であり、グローバル DSQ に入れたタスクが最終的にそこで動くとは限らない。

タスクをカーネルの実行経路へ渡すための待ち行列を **dispatch queue（DSQ）** と呼ぶ。
各 CPU は自分のローカル DSQ からタスクを実行し、空なら組み込みのグローバル DSQ も参照する。
独自 DSQ を作った場合は、`dispatch` がそこからローカル DSQ へタスクを移す。

```text
runnable
   |
   v
enqueue() -> DSQ -> dispatch() -> local DSQ -> CPU
     ^                                           |
     |-------------- slice expires -------------|
```

図の `dispatch` は、独自の DSQ を作った場合に必要になる経路である。
組み込みのグローバル DSQ からはカーネルがローカル DSQ へ移すため、最初に動かす scheduler では `dispatch` を実装しない。

## 本編で使う三種類の DSQ

この先に出てくる DSQ を、本編での使い方に限って整理すると次のようになる。

| DSQ | 誰が用意するか | 本編ではどう入れるか | どう CPU へ渡るか |
| --- | --- | --- | --- |
| ローカル DSQ | カーネル | idle CPU を見つけたときに直接 insert、または `dispatch` から移す | その CPU が実行する |
| グローバル DSQ | カーネル | `enqueue` から insert | CPU が組み込み処理で取得する |
| 独自 DSQ | scheduler | `enqueue` から insert | `dispatch` でローカル DSQ へ移す |

これは `sched_ext` が許すすべての経路を網羅した表ではない。
この本のコードを読むために必要な経路だけを抜き出している。

独自 DSQ もカーネルが提供するデータ構造である。
BPF 側でその作成と受け渡しを指定できるため、複数のキューからどれを先に取り出すか、といった方針を実装できる。

一度の割り当てでタスクが使える CPU 時間を **タイムスライス** と呼ぶ。
本編の実装では、タスクを DSQ に入れるときにスライスを渡す。
途中で眠ったり、優先するスケジューラクラスに CPU を譲ったりすることもあるため、指定した時間だけ連続して実行される保証ではない。
本編の FIFO でスライスを使い切ったタスクは、ほかに待っているタスクがあれば、再び `enqueue` を通って末尾へ並ぶ。
したがって、長いスライスは同じタスクが CPU を保持する時間を延ばし、短いスライスは選び直す機会を増やす。

## scheduler を載せる仕組み

scheduler のコードは BPF C だが、それをカーネルへ載せるのは別のプログラムである。
lab の構成では、スケジューリングの方針を BPF C で書き、それを Rust の loader がカーネルへ渡す。
流れは次のとおりである。

```text
BPF C をコンパイル
    ↓
Rust loader が BPF object を開く
    ↓
partial flag と rodata を設定
    ↓
sched_ext_ops を load、attach
    ↓
loader の生存期間だけ scheduler が有効
```

**rodata** は読み取り専用データ領域であり、この loader は load 前にスライスの初期値を変更できる。
partial flag は次節で扱う `SCX_OPS_SWITCH_PARTIAL` であり、これも loader が設定する。
この loader は、scheduler の接続を表す BPF link をプロセス内に保持する。
loader を終了させれば scheduler は外れ、対象のタスクは通常の scheduler に戻る。
`Ctrl+C` が「実験を止める」操作であると同時に「scheduler を外す」操作でもあるのは、この構造のためである。

## partial switching

最初の実験では、VM 内の全プロセスを自作 scheduler へ移さない。
`SCX_OPS_SWITCH_PARTIAL` を有効にし、明示的に `SCHED_EXT` を選んだ負荷生成器だけを対象にする。
タスクが `SCHED_EXT` を選ぶとは、自プロセスの scheduling policy を `sched_setscheduler(2)` で変更することである。
負荷生成器は起動時にこれを行う。

shell と Multipass の操作経路は通常の fair class（実行可能なタスクへ CPU 時間を分配する Linux 標準のスケジューラクラス）に残る。
自作 scheduler が実験対象を止めても、修正するための端末まで同時に止まりにくい。
ただし fair class が優先されるため、そこに残したタスクの負荷も実験対象の待ち時間へ影響する。

本編以外の経路と callback の条件は、Linux 7.0 の [Scheduling Cycle](https://docs.kernel.org/7.0/scheduler/sched-ext.html#scheduling-cycle) で確認できる。
