# 1秒後に戻れないタスク

1 秒眠って時刻を表示する処理を繰り返す。
別の端末で計算を続けるタスクを動かすと、表示される間隔はどう変わるだろうか。
二つを同じ CPU で動かし、標準のスケジューラと、スライスを変更した自作スケジューラで比べる。

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

`tools/sleep.py` は、現在時刻を表示して1秒眠る処理を、`Ctrl+C` で止めるまで繰り返す Python スクリプトである。
ビルドせず実行でき、中心の処理は次のとおりである。

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

`(+1.001 s)` は前の標本から約1秒たったことを示し、sleep から戻るまでにかかった時間を比べる目安になる。
時刻の表示とは別に、経過時間の測定には、時計の時刻合わせの影響を受けない [`time.monotonic()`](https://docs.python.org/3/library/time.html#time.monotonic) を使っている。

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

sleep が眠り終わったときにも CPU を使う相手として、端末2で `tools/cpu_hog.py` を動かす。
このスクリプトは眠らずにループし続ける。

```python
while True:
    pass
```

```console
taskset -c 0 python3 tools/cpu_hog.py
```

起動メッセージが出たら、ループし続けている。
端末2はそのままにして、端末3で先ほどのコマンドをもう一度実行する。

```console
taskset -c 0 python3 tools/sleep.py
```

二つのプロセスは、どちらも `taskset -c 0` で CPU 0 だけを使うように制限している。
タスクが使える CPU を制限する設定を **CPU affinity** と呼ぶ。
別々の CPU に分かれると順番待ちが起きにくいため、同じ CPU に揃えている。

sleep だけを複数起動しても、眠っている間は CPU が空くため、大きな遅れは見えにくい。
計算タスクが動く今の条件で、表示がおよそ1秒おきに続くかを確かめ、端末3の出力を一行手元に残す。
この出力を、標準のスケジューラでの比較基準にする。

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

`--sched-ext` によって、どちらのスクリプトも冒頭で自分自身を自作スケジューラの対象にする。
端末3の表示間隔と括弧内の経過時間を、標準のスケジューラで残した出力と比べる。
次の行が出るまでの待ち時間に差があるかを確かめ、出力を一つ手元に残す。

## 眠り終わっても CPU を待つ

`time.sleep(1)` の指定は「少なくとも 1 秒眠る」という意味であり、1 秒後の実行再開を予約するものではない。
眠り終わった時点で計算タスクが CPU を使っていると、sleep したタスクは交代を待つ。

```text
端末2の計算タスク : CPU を使い続ける ──────────┐
端末3の sleep    : 1 秒眠る → 眠り終わる → 待つ → 実行再開して表示
                                           ↑
                                     CPU が回ってくる
```

2 秒のスライスでは、計算タスクが長く CPU を使える分、眠り終わったタスクの順番待ちも長くなる。
この待ちが加わるため、sleep から戻るまでには 1 秒より長くかかる。
実測には割り込みや VM がホスト側で待つ時間も含まれるので、毎回同じ値になるとは限らない。

## 起動したタスクを止める

端末3で `Ctrl+C` を押して、時刻の表示を止める。
続いて端末2の計算タスク、端末1のスケジューラを、それぞれ `Ctrl+C` で止める。

端末3で `cat /sys/kernel/sched_ext/state` が `disabled` に戻ったことを確認する。
差が見えなければ、[実験で遅延が見えない場合](../appendix/troubleshooting.md#実験で遅延が見えない)を確認する。

## スライスを短くしてみる

計算タスクのスライスを短くすると、sleep の表示間隔はどう変わるだろうか。
同じ二つのタスクと CPU affinity を保ち、スライスだけを変えて確かめる。
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

表示の間隔がおよそ1秒に戻るかを、2 秒スライスのときの出力と比べる。
結果を一行手元に残す。

確認したら、端末3、端末2、端末1の順に `Ctrl+C` で止める。
端末3で `cat /sys/kernel/sched_ext/state` が `disabled` に戻ったことを確認し、端末2と端末3は `exit` で Mac 側へ戻る。
lab のスライスは 10 ミリ秒のまま保存しておく。
