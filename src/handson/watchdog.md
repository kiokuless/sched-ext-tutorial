# 壊れたスケジューラから戻る

`sched_ext` は、CPU を誰に配るかという OS の中心的な判断を、実行時に読み込んだ BPF scheduler へ任せられる。
それは便利である一方、かなり危険にも見える。
CPU を配るコードそのものを壊せるのなら、どうして試行錯誤しながら開発できるのだろうか。
この章では scheduler のアルゴリズムではなく、その問いに答える。

これまでの章では、`enqueue` されたタスクを必ずどこかの DSQ に入れていた。
`enqueue` には、実行可能になったタスクを待ち行列に置くという契約がある。
この契約を破ったら何が起きるかを、この章では意図的に確かめる。
カーネルの watchdog が scheduler を止めて回収してくれることを一度見ておけば、自作 scheduler を開発するときの安全網として信頼できる。

CPU scheduler は、普通のアプリケーションより失敗の影響が大きい。
Web サーバの一プロセスが止まっても shell から調査できるが、CPU を配る scheduler が runnable task を選ばなくなると、その shell 自身が動けなくなる。
system-wide で scheduler を差し替えるということは、修復に使う道具も同じ scheduler の判断に依存するということである。

`sched_ext` で実験しやすい理由の一つは、この失敗を前提にした復帰経路が用意されていることにある。
BPF verifier は、ロード時に BPF プログラムがカーネル内で許されない動作をしないかを検査する。
一方、watchdog が見るのは、ロードに成功した scheduler が実行中にタスクを長時間進められなくしていないか、という別の種類の失敗である。
「ロードできるコード」と「scheduler として正しく前進するコード」は同じではない。
この章では、その差を意図的な故障で確認する。

この章で観測する流れを先に並べると、次のようになる。

```text
壊れた scheduler を system-wide で load
    ↓
enqueue が runnable task をどこにも置かない
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

verifier が「ロード前の安全性」を担当し、watchdog と abort 経路が「実行中に scheduler として前進できなくなった場合」を回収する。
二つを同じ安全機構としてひとまとめにしないことが重要である。

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

ここまで確認できれば、故障は単なる「VM が数秒固まった」という現象ではなくなる。
runnable task を DSQ に入れなかったこと、進行が止まったこと、watchdog が異常として scheduler を外したこと、loader が停止理由を報告したことを一本の因果関係として追える。
安全機構は、存在を知っているだけでなく、一度壊して復帰まで観測しておくと開発時の前提として使いやすくなる。

ここでいう安全は、「危険なことが起きない」という意味ではない。
自作 scheduler は実際にタスクを止められるし、system-wide なら端末も止められる。
その代わり、失敗を検出して scheduler を外し、既存の scheduling class へ戻る経路が用意されている。
拡張可能性と失敗時の復帰を一組で設計することで、カーネルの中心部分を実験対象にできる。

## 手動で止める

自動復帰しない場合は、ホスト側から次を実行する。

```console
make reset
```
