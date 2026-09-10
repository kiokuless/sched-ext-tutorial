# 壊して、戻る

[VM 全体へ広げる](system-wide.md)で使った system-wide mode では、操作や修復に使う shell も自作スケジューラに従う。
そのスケジューラがタスクを CPU へ渡さなくなると、shell 自身も動けなくなる。
この章では、あらかじめ用意した壊れた完成例を使い、カーネルによる復帰を確かめる。

## タスクを DSQ へ投入しない実装

これまでの `enqueue` は、受け取ったタスクを DSQ へ入れていた。
完成例 `STEP=05` では、その処理を取り除いている。

```c
void BPF_STRUCT_OPS(oreore_enqueue, struct task_struct *p, u64 enq_flags)
{
	/* Intentionally drop every runnable task for the watchdog exercise. */
	(void)p;
	(void)enq_flags;
}
```

この `enqueue` はどの DSQ にもタスクを投入せず、完成例には後から取り出す処理もない。
そのため、タスクは実行可能なまま CPU を待ち続ける。

`enqueue` で直ちに DSQ へ入れない実装自体は認められている。
BPF 側でタスクを保持し、後から `dispatch` で渡すこともできるためである。
この完成例が停滞するのは、後から実行させる処理もなく、タスクを放置しているからである。

## ロード後に停滞を見つける仕組み

BPF verifier がロード時に検査するのは、プログラムに許されない動作がないかである。
検査を通っても、スケジューラとしてタスクを進められるとは限らない。
実行中に実行可能なタスクの停滞を検出するのが、カーネルの watchdog である。

<figure class="technical-figure">
<div class="diagram-scroll" tabindex="0" role="region" aria-label="watchdog が壊れた scheduler から復帰させる流れ（横スクロール可能）">
<img src="../images/watchdog-recovery.svg" alt="上段はタスクが enqueue から DSQ へ進めず停滞する状態。カーネルの watchdog が停滞を検出して自作 scheduler を解除すると、下段のようにタスクが fair class で再び CPU を得る。">
</div>
<figcaption>× はタスクを DSQ へ渡す経路の欠落。watchdog が検出すると、自作 scheduler が外れる。</figcaption>
</figure>

watchdog は異常を検出すると自作スケジューラを外し、対象のタスクを fair class へ戻す。
この `oreore_broken` は、`sched_ext_ops` の `timeout_ms` を 3 秒に設定している。

教材の環境では数秒での復帰を期待するが、3 秒以内に VM が必ず応答を再開する保証ではない。
ホストが VM を実行しない時間なども、実際の待ち時間に影響する。

## 故障を実行する

**この操作は教材 VM で行う。
`MODE=system` では shell や通常のサービスも対象になるため、watchdog が動くまでの数秒間、端末の応答が止まることを見込んでおく。**
リアルタイムクラスなど、`sched_ext` の対象外のタスクまで止める実験ではない。

実行中のスケジューラを終了し、状態が `disabled` に戻ったことを確認する。
その後、端末1（ホスト側のリポジトリ直下）で次を実行する。
`STEP=05` は壊れた完成例を使う指定であり、lab のコードは変更しない。

```console
make run STEP=05 MODE=system
```

応答が止まったら復帰を待つ。
自動復帰しない場合は、ホスト側の別の端末から次を実行する。

```console
make reset
```

## 復帰した証拠を読む

端末が動き始めたら、スケジューラの状態と停止理由を確認する。
端末2から VM に入り、まず状態を読む。

```console
make vm-shell
cat /sys/kernel/sched_ext/state
```

`disabled` なら、自作スケジューラは外れている。
続いて、端末1に表示された停止理由を見る。
2026 年 9 月 6 日の教材 VM では次の出力があり、`state` は `disabled` に戻った。

```text
Error: EXIT: runnable task stall (watchdog failed to check in for 3.001s)
make: *** [run] Error 1
```

`runnable task stall` は、watchdog がタスクの停滞を検出したことを示す。
`Error 1` は、異常停止を loader がエラーとして報告した結果であり、この行だけでは停止理由も復帰の成否も分からない。
自分の出力でも、stall の報告と `disabled` の両方を確認する。

手動で `make reset` を使った場合は、自動復帰を確認した記録とは分けて残す。
確認が終わったら、端末2で `exit` を実行し、ホスト側へ戻る。

<details>
<summary>停止理由が loader へ届くまで</summary>

[最初の main.bpf.c を読む](../handson/model.md)で読んだ `exit` callback が、スケジューラの外れた理由を `UEI_RECORD` で記録する。
loader 側の **`uei_report`** は、その exit 情報を人間が読める形で出力する。

タスクを後で渡すための保持方法は、Linux 7.0 の [Scheduling Cycle](https://docs.kernel.org/7.0/scheduler/sched-ext.html#scheduling-cycle) に記載されている。

</details>
