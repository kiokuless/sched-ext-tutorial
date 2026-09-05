# スライスを短くする

周期タスクを早く再開させる最も単純な方法は、CPU-bound タスクから頻繁に CPU を取り上げることだ。
スライスを10ミリ秒へ縮める。

```console
make restore STEP=04
```

```c
const volatile u64 slice_ns = 10000000ULL;  /* 10 milliseconds */
```

同じ15秒の実験を繰り返す。

```console
make bench CASE=step STEP=04
```

長いスライスの結果と比べ、次の値を記録する。

| 条件 | 最大遅延 | deadline miss | context switches |
|---|---:|---:|---:|
| fair class |  |  |  |
| 2秒スライス |  |  |  |
| 10ミリ秒スライス |  |  |  |

最大遅延が減っても、コンテキストスイッチ数は増えるはずだ。
二つの CPU hog が短いスライスで交互に実行されるため、2秒スライスより多くの context switch が観測される。
実測がそうならなかった場合は、CPU hog が二つ動いているか、CPU 固定と scheduler の状態を確認する。

短いスライスが常に優れているわけではない。
選び直す機会を増やした代わりに、切り替えの処理とキャッシュ状態の損失を増やしている。

