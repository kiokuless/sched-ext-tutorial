# 1秒後に戻れないタスク

1 秒眠って時間を表示する処理を繰り返す。
別の端末で計算を続けるタスクを動かすと、表示される間隔はどう変わるだろうか。
端末を三つ並べ、自分で起動して確かめてみよう。

## 三つの端末を用意する

前章のスケジューラは `Ctrl+C` で終了しておく。
端末1は Mac 側のリポジトリ直下、端末2と端末3はそれぞれ `make vm-shell` で VM に入る。

| 端末 | 場所 | 動かすもの |
|---|---|---|
| 端末1 | Mac | 自作スケジューラ |
| 端末2 | VM | 計算を続けるタスク |
| 端末3 | VM | 1 秒の sleep を繰り返すタスク |

端末2と端末3では、次のコマンドでリポジトリのディレクトリへ移動しておく。

```console
cd /workspace/sched-ext-tutorial
```

## 時刻を表示するスクリプト

`tools/sleep.py` は、この教材に入っている短い Python スクリプトである。
現在時刻を表示して1秒眠る処理を、`Ctrl+C` で止めるまで繰り返す。
中心の処理は次のとおりで、ビルドは必要ない。

```python
{{#include ../../tools/sleep.py:18:30}}
```

1行目には現在時刻と `sample1`、2行目以降には前回からの経過時間も表示する。
出力の形は次のようになる（時刻と数値は例）。

```text
[12:00:00.000] sample1
[12:00:01.001] sample2  (+1.001 s)
[12:00:02.002] sample3  (+1.001 s)
```

表示には時計の時刻を使い、経過時間には時計の時刻合わせの影響を受けない [`time.monotonic()`](https://docs.python.org/3/library/time.html#time.monotonic) を使っている。
`(+1.001 s)` は、前の標本から約1秒たったという意味である。

## まず sleep だけを動かす

端末3で、スケジューラが外れていることを確認する。

```console
cat /sys/kernel/sched_ext/state
```

`disabled` なら、続けてスクリプトを実行する。

```console
taskset -c 0 python3 tools/sleep.py
```

現在時刻が、およそ1秒おきに表示されることを確かめる。
数行見たら `Ctrl+C` で止める。

## 計算タスクを同時に動かす

端末2では、もう一つのスクリプト `tools/cpu_hog.py` を使う。
こちらの中心は、眠らずにループし続ける次の処理である。

```python
while True:
    pass
```

このループで CPU を使い続ける相手を作る。

```console
taskset -c 0 python3 tools/cpu_hog.py
```

起動メッセージが出たら、ループし続けている。
端末2はそのままにして、端末3で先ほどのコマンドをもう一度実行する。

```console
taskset -c 0 python3 tools/sleep.py
```

これで二つのプロセスが同時に動いている。
両方の `taskset -c 0` は、CPU 0 だけを使う指定である。
この制限を **CPU affinity** と呼ぶ。
別々の CPU に分かれると順番待ちが起きにくいので、同じ CPU を使わせている。

sleep だけを複数起動しても、眠っている間は CPU が空くため、大きな遅れは見えにくい。
計算タスクを置くと、sleep が眠り終わったときにも CPU を使う相手がいる。
標準のスケジューラでは、この状態でもおよそ1秒おきに表示が続くだろうか。
端末3の出力を一行、手元に残す。

数行見たら、端末3と端末2でそれぞれ `Ctrl+C` を押して止める。

## 自作スケジューラのスライスを 2 秒にする

自作スケジューラでは、一度にタスクへ割り当てる CPU 時間を変更できる。
この時間を **タイムスライス** と呼ぶ。
Mac 側で `lab/src/bpf/main.bpf.c` の次の行を探す。
途中から始める場合は、編集内容を別のファイルへ保存したうえで `make restore STEP=01` を使う。

```c
const volatile u64 slice_ns = 20000000ULL;  /* 20 ms, kernel default */
```

単位はナノ秒で、現在は 20 ミリ秒である。
計算タスクが長く CPU を使えるよう、2 秒に変更して保存する。

```c
const volatile u64 slice_ns = 2000000000ULL;  /* 2 seconds */
```

端末1で、自作スケジューラを起動する。

```console
make run STEP=lab MODE=partial
```

`scx_oreore started (mode=partial, slice=2000000 us)` が出たら、そのまま動かしておく。
完成例を直接使う場合は `STEP=02` を指定できる。

端末2で、今度は `--sched-ext` を付けて計算タスクを起動する。

```console
sudo taskset -c 0 python3 tools/cpu_hog.py --sched-ext
```

その計算を続けたまま、端末3でも `--sched-ext` を付けて sleep を起動する。

```console
sudo taskset -c 0 python3 tools/sleep.py --sched-ext
```

`--sched-ext` は、スクリプトの冒頭で自分自身を自作スケジューラの対象にする指定である。
これで二つとも対象になった。
端末3の表示が出る間隔と、括弧内の経過時間を見てみよう。
標準のスケジューラで動かしたときより、次の行が出るまで長く待たされるだろうか。
出力を一つ手元に残す。

## 眠り終わっても CPU を待つ

1 秒眠り終わっても、その瞬間に CPU を使えるとは限らない。
計算タスクが CPU を使っていると、sleep したタスクは交代を待つ。

```text
端末2の計算タスク : CPU を使い続ける ──────────┐
端末3の sleep    : 1 秒眠る → 眠り終わる → 待つ → 実行再開して表示
                                           ↑
                                     CPU が回ってくる
```

`time.sleep(1)` の指定は「少なくとも 1 秒眠る」という意味である。
その後の順番待ちが加わるため、戻るまでの時間は 1 秒より長くなる。
2 秒のスライスでは、計算タスクが長く CPU を使える分、眠り終わったタスクも待たされる。
実測には割り込みや VM がホスト側で待つ時間も含まれるので、毎回同じ値になるとは限らない。

## 起動したタスクを止める

端末3で `Ctrl+C` を押して、時刻の表示を止める。
続いて端末2の計算タスク、端末1のスケジューラを、それぞれ `Ctrl+C` で止める。

端末3で `cat /sys/kernel/sched_ext/state` が `disabled` に戻ったことを確認する。
差が見えなければ、[実験で遅延が見えない場合](../appendix/troubleshooting.md#実験で遅延が見えない)を確認する。

## スライスを短くしてみる

Mac 側で `lab/src/bpf/main.bpf.c` の `slice_ns` を 10 ミリ秒へ変えて保存する。

```c
const volatile u64 slice_ns = 10000000ULL;  /* 10 milliseconds */
```

端末1で `make run STEP=lab MODE=partial` を再実行し、起動ログが `slice=10000 us` になったことを確認する。
端末2と端末3は VM に入ったまま、先ほどと同じスクリプトを起動する。

端末2：

```console
sudo taskset -c 0 python3 tools/cpu_hog.py --sched-ext
```

端末3：

```console
sudo taskset -c 0 python3 tools/sleep.py --sched-ext
```

表示の間隔は、およそ1秒に戻っただろうか。
2 秒スライスのときの出力と比べ、一行手元に残す。

確認したら、端末3、端末2、端末1の順に `Ctrl+C` で止める。
端末3で `cat /sys/kernel/sched_ext/state` が `disabled` に戻ったことを確認し、端末2と端末3は `exit` で Mac 側へ戻る。
lab のスライスは 10 ミリ秒のまま保存しておく。
