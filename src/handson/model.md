# `sched_ext` が変えるもの

VM の準備が整ったので、次章で最初の scheduler を動かす前に、`sched_ext` がカーネルのどこを差し替えるのかを整理しておく。

通常のプロセスは、実行可能になっただけでは CPU 上で動けない。
スケジューラが待ち行列からプロセスを選び、CPU へ渡して初めて命令を実行できる。
`sched_ext` は、この選択に BPF プログラムを差し込む。
この BPF プログラムが実装する入口の集合を **`sched_ext_ops`** と呼ぶ。

今回使う callback は三つである。

- **`select_cpu`**：起床したタスクを動かす CPU の候補を選ぶ
- **`enqueue`**：実行可能なタスクを待ち行列へ入れる
- **`dispatch`**：待ち行列からタスクを CPU のローカルキューへ移す

待ち行列には **dispatch queue（DSQ）** という名前が付いている。
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
組み込みのグローバル DSQ は CPU が直接参照するため、次章で最初に動かす scheduler では `dispatch` を実装しない。
図の全体を最初から実装する必要はない、ということである。

タスクが CPU を使ってよい連続した時間を **タイムスライス** と呼ぶ。
タスクは待ち行列に入れられるときにスライスを渡され、CPU に載るとその分だけ動く。
スライスが尽きたとき、まだ実行可能なら再び `enqueue` へ戻る。
したがって、長いスライスは同じタスクが CPU を保持する時間を延ばし、短いスライスは選び直す機会を増やす。
この本の実験は、この一文を数値で確かめることになる。

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
sched_ext_ops を load・attach
    ↓
loader の生存期間だけ scheduler が有効
```

rodata とは、loader が load 前にだけ書き換えられる定数領域のことで、タイムスライスのような設定値の受け渡しに使う。
partial flag は次節で扱う `SCX_OPS_SWITCH_PARTIAL` であり、これも loader が設定する。
最後の行が実用上いちばん重要である。
scheduler は loader プロセスの生存期間しか有効でない。
loader を終了させれば scheduler は外れ、対象のタスクは通常の scheduler に戻る。
`Ctrl+C` が「実験を止める」操作であると同時に「scheduler を外す」操作でもあるのは、この構造のためである。

## partial switching

最初の実験では、VM 内の全プロセスを自作 scheduler へ移さない。
`SCX_OPS_SWITCH_PARTIAL` を有効にし、明示的に `SCHED_EXT` を選んだ負荷生成器だけを対象にする。
タスクが `SCHED_EXT` を選ぶとは、自プロセスの scheduling policy を `sched_setscheduler(2)` で変更することである。
負荷生成器は起動時にこれを行う。

shell と Multipass の操作経路は通常の fair class（実行可能なタスクへ CPU 時間を分配する Linux 標準のスケジューラクラス）に残る。
自作 scheduler が実験対象を止めても、修正するための端末まで同時に止まりにくい。
まず partial で安全に実験し、仕組みが分かったところで VM 全体を切り替える、という順序をこの本は取る。
