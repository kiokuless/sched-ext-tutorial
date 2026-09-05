# 壊れたスケジューラから戻る

これまでの章では、`enqueue` されたタスクを必ずどこかの DSQ に入れていた。
`enqueue` には、実行可能になったタスクを待ち行列に置くという契約がある。
この契約を破ったら何が起きるかを、この章では意図的に確かめる。
カーネルの watchdog が scheduler を止めて回収してくれることを一度見ておけば、自作 scheduler を開発するときの安全網として信頼できる。

最後の checkpoint は、`enqueue` されたタスクをどの DSQ にも入れない。
実行可能なタスクは CPU を待ち続ける。

```c
void BPF_STRUCT_OPS(oreore_enqueue, struct task_struct *p, u64 enq_flags)
{
    /* Intentionally drop every runnable task for the watchdog exercise. */
    (void)p;
    (void)enq_flags;
}
```

この壊れ方は偶然ではなく、watchdog の動作を見るために意図的に作っている。
通常の scheduler 実装で runnable task を放置してよいという意味ではない。

runnable なタスクが放置され続けると、カーネルの watchdog が異常を検出して scheduler を外し、タスクを fair class へ戻す。
`oreore_broken` は timeout を3秒に設定している。
したがって、この scheduler が載ったまま止まるのは数秒だけである。

## 実行する

```console
make run STEP=05 MODE=system
```

MODE=system であることに注意する。
実験対象だけではなく、VM 内のすべての実行可能タスクが CPU を得られなくなる。
watchdog が動くまでの数秒間、shell を含めて端末の応答が止まるが、これは想定内の挙動である。
復帰を待つ。

復帰したら、別の端末で状態を確認する。

```console
cat /sys/kernel/sched_ext/state
```

実行端末には、`uei_report` が取得した停止理由が表示される。
`uei_report` は、scheduler がカーネルから受け取った exit 情報を人間が読める形に整形して出力する loader 側の補助である。
global.md で読み飛ばした `exit` callback は、この exit 情報を記録するためのものだった。

## 手動で止める

自動復帰しない場合は、ホスト側から次を実行する。

```console
make reset
```

`reset` は、動作中の scheduler 名が `oreore` で始まる場合だけ `SysRq-S` を送る（scx_utils が ops 名にバージョンとターゲット情報を付加するため、前方一致で判定する）。
SysRq-S は、`sched_ext` の scheduler を強制的に切り離すカーネルの緊急手順である。
別の scheduler が動いている場合は停止を拒否する。
