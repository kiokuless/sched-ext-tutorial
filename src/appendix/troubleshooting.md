# トラブルシューティング

## `make doctor` が何かを fail する

`make vm-bootstrap` が完了していないと、検査対象のツールが揃っていないことがある。
まず bootstrap を完了させてから、`make doctor` を再実行する。
それでも fail する場合は、`multipass shell` で VM に入り、各条件を個別に確認する。

`CONFIG_SCHED_CLASS_EXT=y` が有効でなければ、Ubuntu 26.04 の標準カーネルを使っているかを確認する。
古い Ubuntu イメージや WSL から起動した環境では、このオプションが無効になっている可能性がある。

## BPF verifier がロードを拒否する

まず、`make restore STEP=01` と `make build STEP=lab` が成功するか確認する。**
`restore` は lab の BPF ファイルを上書きするため、調べたい変更を実行前に別のファイルへ保存しておく。**
最小構成が通る場合は、直前に変更した BPF コードが verifier の制約に反していないかを調べる。

詳細なログを出すために `-v` を指定する場合は、VM 内で loader を直接実行する。

```console
sudo /var/cache/sched-ext-tutorial/target/scx-step-lab/release/scx_oreore --partial -v
```

## スライスを変えたのに起動ログが古い

`make build` だけでは、既定の `STEP=01` をビルドする。
編集した lab を使うには、`make run STEP=lab MODE=partial` を実行する。
このコマンドには lab のビルドも含まれる。

`slice_ns = 2000000000ULL` は 2 秒であり、起動ログでは `slice=2000000 us` と表示される。
値が合わなければ、エディタで保存したファイルが `lab/src/bpf/main.bpf.c` かを確認する。
コメントに書いた時間は動作に影響しないが、数値と揃えて更新しておく。

VM 内のビルドキャッシュよりソースの更新日時が古いと、Cargo が変更前の BPF を再利用することがある。
教材のビルドスクリプトは、C ファイルの内容のハッシュも監視し、更新日時だけに依存せず変更を検知する。

## scheduler が残っている

教材のスケジューラを解除するには、次を実行する。

```console
make reset
```

`make reset` は、動作中のスケジューラ名が教材の名前と一致した場合だけ `SysRq-S` を送る。
別の `sched_ext` スケジューラが動いている場合は、そのスケジューラの終了手順を使う。

## 実験で遅延が見えない

遅延が観測されないときは、次の順で実験条件を確認する。

1. `/sys/kernel/sched_ext/state` が `enabled` になっている。
2. `root/ops` が `oreore` で始まっている。
3. 負荷生成器が `--sched-ext` 付きで動いている。
4. 計算タスクと sleep タスクが `taskset -c 0` で固定されている。
5. `STEP=02` の 2 秒スライスを使っている。

前提が揃っていても、測定にはホスト側の停止時間が混ざる場合がある。
一度だけ数値が外れたことを、スケジューラの効果と断定しない。
