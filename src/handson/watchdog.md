# 壊れたスケジューラから戻る

`sched_ext` は、CPU を誰に配るかという OS の中心的な判断を、実行時に読み込んだ BPF scheduler へ任せられる。
それは便利である一方、かなり危険にも見える。
CPU を配るコードそのものを壊せるのなら、どうして試行錯誤しながら開発できるのだろうか。

これまでの章では、`enqueue` されたタスクを必ずどこかの DSQ に入れていた。
今度は受け取ったタスクを放置し、CPU へ戻す経路をなくしてみる。
ロードできても仕事を進められないスケジューラを、カーネルがどう検出するか確かめる。

CPU scheduler は、普通のアプリケーションより失敗の影響が大きい。
Web サーバの一プロセスが止まっても shell から調査できるが、CPU を配る scheduler が runnable task を選ばなくなると、その shell 自身が動けなくなる。
system-wide で scheduler を差し替えるということは、修復に使う道具も同じ scheduler の判断に依存するということである。

`sched_ext` で実験しやすい理由の一つは、この失敗を前提にした復帰経路が用意されていることにある。
BPF verifier は、ロード時に BPF プログラムがカーネル内で許されない動作をしないかを検査する。
一方、watchdog が見るのは、ロードに成功した scheduler が実行中にタスクを長時間進められなくしていないか、という別の種類の失敗である。
「ロードできるコード」と「scheduler として正しく前進するコード」は同じではない。

故障させると、次の順で復帰することを期待する。

```text
壊れた scheduler を system-wide で load
    ↓
enqueue で受け取った runnable task を放置する
    ↓
タスクが CPU を得られず、VM の応答が止まる
    ↓
watchdog が stall を検出
    ↓
sched_ext scheduler を abort
    ↓
タスクが fair class へ戻る
    ↓
loader が停止理由を表示
```

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

`enqueue` で直ちに DSQ へ入れないこと自体は、API の違反ではない。
BPF 側でタスクを保持し、後から `dispatch` で渡す実装も認められている。
この checkpoint の問題は、後から渡す経路もなく、タスクを待たせ続けることである。
許される保持方法は Linux 7.0 の [Scheduling Cycle](https://docs.kernel.org/7.0/scheduler/sched-ext.html#scheduling-cycle) に記載されている。

runnable なタスクが放置され続けると、カーネルの watchdog が異常を検出して scheduler を外し、タスクを fair class へ戻す。
`oreore_broken` は timeout を3秒に設定している。
教材の環境では数秒での復帰を期待するが、3 秒は VM が必ずその時間内に応答を再開する保証ではない。
ホストが VM を実行しない時間なども、実際の待ち時間に影響する。

## 実行する

```console
make run STEP=05 MODE=system
```

MODE=system であることに注意する。
通常の shell やサービスも自作 scheduler の対象に入る。
リアルタイムクラスなど、`sched_ext` の対象外のタスクまで止める実験ではない。
watchdog が動くまでの数秒間、shell を含めて端末の応答が止まるが、これは想定内の挙動である。
復帰を待つ。

復帰したら、別の端末から VM に入り、状態が `disabled` に戻ったことを確認する。

```console
make vm-shell
cat /sys/kernel/sched_ext/state
```

実行端末には、`uei_report` が取得した停止理由が表示される。
`uei_report` は、scheduler がカーネルから受け取った exit 情報を人間が読める形に整形して出力する loader 側の補助である。
[最小のスケジューラ](./global.md)で使った `exit` callback は、この情報を記録していた。
停止理由が runnable task の stall を示すことを読み取り、単なる手動終了やロード失敗と区別する。

2026 年 9 月 6 日の教材 VM では、停止理由に次の行が出た。
このとき `state` は `disabled` に戻った。

```text
Error: EXIT: runnable task stall (watchdog failed to check in for 3.001s)
make: *** [run] Error 1
```

異常停止を loader がエラーとして報告するため、`make run` も正常終了にはならない。
この実験では、その終了ステータスだけで復帰失敗とは判断せず、stall の報告と状態の復帰を確かめる。

端末が再び動いただけでは、watchdog による復帰を確認したことにはならない。
停止理由と `disabled` への変化を合わせて記録すると、タスクの放置が検出され、スケジューラが外されたことを確認できる。

## 手動で止める

自動復帰しない場合は、ホスト側から次を実行する。

```console
make reset
```
