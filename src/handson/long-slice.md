# 1秒後に戻れないタスク

共有 DSQ は FIFO である。
一つのタスクが CPU を長く保持すれば、その途中で起床したタスクはキューで待つ。

実験では、二つの CPU-bound タスクと1秒周期のタスクを CPU 0に固定する。

```console
taskset -c 0 ./cpu-hog   # 1個目
taskset -c 0 ./cpu-hog   # 2個目
taskset -c 0 ./periodic-task
```

`taskset` は scheduler を変更しない。
プロセスが実行できる CPU を CPU 0だけに制限し、三つのタスクが同じ CPU を奪い合う条件を作る。
二つの CPU-bound タスクが同時に存在すると、タイムスライスの切れ目でコンテキストスイッチが発生しやすくなる。

## 2秒のスライス

```console
make restore STEP=03
```

この checkpoint は、dispatch 時に渡すスライスを2秒へ変更している。

```c
const volatile u64 slice_ns = 2000000000ULL;  /* 2 seconds */
```

周期タスクが1秒後に runnable になっても、CPU-bound タスクの2秒スライスが残っていればすぐには走れない。
`sleep(1)` がタイマーを遅らせたのではなく、タイマー満了後の dispatch が遅れる。

## 通常の Linux と比較する

まず、`sched_ext` を使わずに負荷生成器を動かす。

```console
make bench CASE=fair
```

続いて長いスライスの scheduler を使う。

```console
make bench CASE=step STEP=03
```

負荷生成器は15回の起床について、予定時刻からの遅れと deadline miss を表示する。
最後に `perf stat` が CPU 0のコンテキストスイッチ数を表示する。

15標本では p95 や p99 を安定して評価できない。
ここで比べるのは、個々の遅延、最大遅延、deadline miss 数である。

