# 最初のスケジューラを動かす

Windows では、[Windows 向け手順のコマンド対応表](./windows.md#本文のコマンドを読み替える)を使う。
以下の Mac 側の編集と `make` 操作は、Windows 向け手順では VM 内の端末1で行う。

用意されたスケジューラを VM に載せ、一つのタスクを動かす。
起動できたことは名前で、タスクが進んだことは出力で確かめる。
終了後に元へ戻るところまで、一度通してみよう。

## 編集するファイルと完成例

Mac 上で取得した `sched-ext-tutorial` を普段のエディタで開く。
本文の `make` コマンドは、Mac 側のリポジトリ直下で実行する。
VM のシェルに入っている場合は、`exit` で Mac 側へ戻っておく。

編集するのは `lab`、各段階の完成例は `checkpoints` に入っている。

```text
sched-ext-tutorial/
├── lab/
│   └── src/
│       ├── bpf/main.bpf.c   ← スケジューラの方針
│       └── main.rs         ← カーネルへ読み込むプログラム
└── checkpoints/
    ├── step-01-global/     ← 最初に動かす完成例
    ├── step-02-shared-dsq/ ← 独自の待ち行列を追加した完成例
    └── …
```

`step-01-global` を lab へコピーする。
`make restore` は lab の BPF ファイルを上書きするため、すでに編集した内容を残す場合は先に別のファイルへ保存する。

```console
make restore STEP=01
```

これでエディタ上の lab が最初の完成例と同じになった。
コードを変更するのは、起動と終了を確かめた後でよい。

## ビルドしてロードする

Mac 側で端末を二つ開き、どちらもリポジトリ直下へ移動する。
端末1はスケジューラを動かしたままにし、端末2から状態を確認する。

| 端末 | 作業する場所 | 役割 |
|---|---|---|
| 端末1 | Mac のリポジトリ直下 | ビルド、起動、終了 |
| 端末2 | `make vm-shell` で入る VM 内 | 状態の確認とタスクの実行 |

端末1でビルドする。

```console
make build STEP=lab
```

`STEP=lab` は、手元の lab を使う指定である。
`STEP=01` とすると、lab に編集を加えていても checkpoint 側を使う。
自分のコードを試すときは `STEP=lab` と覚えておこう。

ビルドは VM にマウントされたソースを使い、VM 内で行われる。
エラーなくプロンプトへ戻れば、実行ファイルができている。
まだスケジューラは有効になっていない。

BPF プログラムをカーネルへ読み込む役割を持つプログラムを **loader** と呼ぶ。
この教材では `lab/src/main.rs` の Rust プログラムが担当する。
端末1から loader を起動する。

```console
make run STEP=lab MODE=partial
```

`make run` はビルドも行い、その後 VM 内で loader を起動する。
`MODE=partial` では、明示的に **`SCHED_EXT`** というスケジューリング方針を選んだタスクだけが、自作スケジューラの対象になる。
このように対象を絞る使い方を **partial switching** と呼ぶ。

操作に使う shell は、通常のタスクへ CPU 時間を分配する Linux 標準の **fair class** に残る。
実験対象だけを自作の方針で動かすため、端末まで同時に止まりにくい。
fair class の負荷も CPU を使うので、実験の待ち時間には影響する。

起動すると、端末1に次の行が出る。

```text
scx_oreore started (mode=partial, slice=20000 us)
```

この後にプロンプトが戻らないのは、loader がスケジューラへの接続を保って待っているためである。
端末1はそのままにしておく。

端末2で VM に入る。

```console
make vm-shell
```

以降、この章の端末2の操作は VM 内で行う。
まず状態を読む。

```console
cat /sys/kernel/sched_ext/state
cat /sys/kernel/sched_ext/root/ops
```

`state` が有効かどうか、`root/ops` が現在のスケジューラ名を示す。

```console
$ cat /sys/kernel/sched_ext/state
enabled
$ cat /sys/kernel/sched_ext/root/ops
oreore_0.1.0_aarch64_unknown_linux_gnu
```

`enabled` と `oreore` で始まる名前が確認できれば、ロードに成功している。
名前の後半はバージョンやビルド環境によって変わる。
起動ログが出ずに終了した場合や `enabled` にならない場合は、端末1のエラーを[トラブルシューティング](../appendix/troubleshooting.md)と照らし合わせる。

## 対象タスクを一つ動かす

ロードはできた。
では、shell が動いているだけで、自作スケジューラがタスクを動かしたと確認できるだろうか。

partial mode の shell は fair class に残っている。
そこで、明示的に `SCHED_EXT` を選ぶタスクを一つ起動する。
教材の負荷生成器には、1 秒間隔の予定時刻に処理を再開し、その遅れを出力する **`periodic`** がある。

端末2で負荷生成器をビルドする。

```console
cd /workspace/sched-ext-tutorial
./scripts/guest/build-workload.sh
```

続けて、周期タスクを実行する。

```console
sudo /var/cache/sched-ext-tutorial/target/workload/release/sched-ext-workload \
    periodic --samples 3 --sched-ext
```

`--samples 3` は三つの標本を記録する指定で、`--sched-ext` はこのタスクを自作スケジューラの対象へ入れる指定である。
見出しに続いて三つの標本と集計が出て、エラーなくプロンプトへ戻ることを確かめる。
これで、対象タスクが処理を進め、終了したことを確認できる。

## 終了して元のスケジューラへ戻す

周期タスクが終了しても、端末1の loader は接続を保っている。
端末1で `Ctrl+C` を押すと、その接続が解放され、自作スケジューラが外れる。

終了後の `state` は、先ほどと同じ `enabled` か、それとも `disabled` か。
端末1で `Ctrl+C` を押してから、端末2で確認する。

```console
$ cat /sys/kernel/sched_ext/state
disabled
```

`disabled` に戻れば、解除まで確認できた。
解除後は `root/ops` がなくなるので、ここでは `state` を読む。
終了できない場合は、Mac 側の別の端末から `make reset` を実行する。

端末2で `exit` を実行し、Mac 側へ戻っておく。
起動時の名前、周期タスクの三つの標本、終了後の `disabled` を確認できたら、起動から解除までを自分でたどれたことになる。

<details>
<summary>loader が保持しているもの</summary>

loader は、BPF object を開き、設定を与えてから load、attach する。
partial mode では、load 前に `SCX_OPS_SWITCH_PARTIAL` を設定する。
負荷生成器側は、`--sched-ext` を指定すると `sched_setscheduler(2)` で自分の方針を `SCHED_EXT` に変更する。

attach で作られた **BPF link** が、スケジューラとの接続を表す。
この loader は link をプロセス内に保持し、終了時に解放する。
`Ctrl+C` でスケジューラを外せるのは、この構造のためである。

</details>
