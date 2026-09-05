# 壊れたスケジューラから戻る

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

```console
make run STEP=05 MODE=system
```

`oreore_broken` は timeout を3秒に設定している。
カーネルが runnable task の stall を検出すると scheduler を外し、タスクを fair-class scheduler へ戻す。
実行端末には `uei_report` が取得した停止理由が表示される。

別の端末で状態を確認する。

```console
cat /sys/kernel/sched_ext/state
```

自動復帰しない場合は、ホスト側から次を実行する。

```console
make reset
```

`reset` は、動作中の scheduler 名が `oreore` で始まる場合だけ `SysRq-S` を送る（scx_utils が ops 名にバージョンとターゲット情報を付加するため、前方一致で判定する）。
別の scheduler が動いている場合は停止を拒否する。

