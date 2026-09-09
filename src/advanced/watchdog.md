# 壊して、戻る

[VM 全体へ広げる](./system-wide.md)で使った system-wide mode では、操作や修復に使う shell も自作スケジューラに従う。
そのスケジューラがタスクを CPU へ渡さなくなると、shell 自身も動けなくなる。
あらかじめ用意した壊れた完成例で、カーネルによる復帰を確かめる。

## タスクを DSQ へ投入しない実装

これまでの `enqueue` は、受け取ったタスクを DSQ に入れていた。
完成例 `STEP=05` は、その処理を取り除いている。

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

`enqueue` で直ちに DSQ へ入れない実装でも、BPF 側で保持し、後から `dispatch` でタスクを渡すことは認められている。
この完成例で停滞する原因は、後から実行させる処理もなく、タスクを放置していることにある。

## ロード後に停滞を見つける仕組み

BPF verifier の検査を通ったプログラムでも、スケジューラとしてタスクを進められるとは限らない。
verifier がロード時に許されない動作がないかを検査するのに対し、カーネルの watchdog は、実行中に実行可能なタスクの停滞を検出する。

<figure class="technical-figure">
<div class="diagram-scroll" tabindex="0" role="region" aria-label="watchdog が壊れた scheduler から復帰させる流れ（横スクロール可能）">
<img src="../images/watchdog-recovery.svg" alt="上段はタスクが enqueue から DSQ へ進めず停滞する状態。カーネルの watchdog が停滞を検出して自作 scheduler を解除すると、下段のようにタスクが fair class で再び CPU を得る。">
</div>
<figcaption>× はタスクを DSQ へ渡す経路の欠落。watchdog が検出すると、自作 scheduler が外れる。</figcaption>
</figure>

watchdog は異常を検出すると自作スケジューラを外し、対象のタスクを fair class へ戻す。
この `oreore_broken` は、`sched_ext_ops` の `timeout_ms` を 3 秒に設定している。
教材の環境では数秒での復帰を期待するが、3 秒以内に VM が必ず応答を再開する保証ではない。
ホストが VM を実行しない時間なども、実際の待ち時間へ影響する。

## 故障を実行する

この操作は教材 VM の中で行われる。
`MODE=system` なので shell や通常のサービスも対象となり、watchdog が動くまでの数秒間、端末の応答が止まることを見込んでおく。
リアルタイムクラスなど、`sched_ext` の対象外のタスクまで止める実験ではない。

実行中のスケジューラを終了し、状態が `disabled` に戻ったことを確認してから、端末1（Mac 側のリポジトリ直下）で起動する。
`STEP=05` は壊れた完成例を使う指定で、lab のコードは変更しない。

```console
make run STEP=05 MODE=system
```

応答が止まったら復帰を待つ。
自動復帰しない場合は、Mac 側の別の端末から次を実行する。

```console
make reset
```

## 復帰した証拠を読む

端末が動き始めたら、状態と停止理由の二つを読む。
端末2から VM に入り、状態を確認する。

```console
make vm-shell
cat /sys/kernel/sched_ext/state
```

`disabled` に戻っていれば、自作スケジューラは外れている。
続いて、端末1に表示された停止理由を見る。

2026 年 9 月 6 日の教材 VM では、次の出力があり、`state` は `disabled` に戻った。

```text
Error: EXIT: runnable task stall (watchdog failed to check in for 3.001s)
make: *** [run] Error 1
```

`runnable task stall` は、watchdog がタスクの停滞を検出したことを示す。
`Error 1` は異常停止を loader がエラーとして報告した結果であり、それだけでは停止理由も復帰の成否も分からない。

自分の出力でも、stall の報告と `disabled` の組み合わせを確認する。
手動で `make reset` した場合は、自動復帰を確認した記録と分けておく。
確認後は端末2で `exit` を実行し、Mac 側へ戻る。

<details>
<summary>停止理由が loader へ届くまで</summary>

[最初の main.bpf.c を読む](../handson/model.md)で読んだ `exit` callback は、スケジューラが外れた理由を `UEI_RECORD` で記録する。
loader 側の **`uei_report`** が、その exit 情報を人間が読める形で出力する。

タスクを後で渡すための保持方法は、Linux 7.0 の [Scheduling Cycle](https://docs.kernel.org/7.0/scheduler/sched-ext.html#scheduling-cycle) に記載されている。

</details>
