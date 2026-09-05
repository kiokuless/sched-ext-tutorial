# `sched_ext` が変えるもの

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

タイムスライスが尽きたタスクは、まだ実行可能なら再び `enqueue` へ戻る。
したがって、長いスライスは同じタスクが CPU を保持する時間を延ばし、短いスライスは選び直す機会を増やす。

## partial switching

最初の実験では、VM 内の全プロセスを自作 scheduler へ移さない。
`SCX_OPS_SWITCH_PARTIAL` を有効にし、明示的に `SCHED_EXT` を選んだ負荷生成器だけを対象にする。

shell と Multipass の操作経路は通常の fair-class scheduler に残る。
自作 scheduler が実験対象を止めても、修正するための端末まで同時に止まりにくい。

