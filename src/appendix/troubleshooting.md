# トラブルシューティング

## `make doctor` が何かを fail する

`make vm-bootstrap` を完了させてから `make doctor` を再度実行する。
bootstrap が完了していない状態では、検査対象のツールが揃っていないことがある。
それでも fail する場合は、`multipass shell` で VM に入り、各条件を個別に確認する。

`CONFIG_SCHED_CLASS_EXT=y` が有効でない場合は、Ubuntu 26.04 の標準カーネルを使っているか確認する。
古い Ubuntu イメージや WSL から起動した環境では、このオプションが無効になっている可能性がある。

## BPF verifier がロードを拒否する

まず `make restore STEP=01` と `make build STEP=lab` が成功するか確認する。
最小構成が通るなら、環境ではなく直前に変更した BPF コードに問題がある。
そのコードが verifier の制約に反していないか、直前の変更から確認する。

`make run STEP=lab MODE=partial` に `-v` を渡したい場合は、VM 内で次を実行する。

```console
sudo /var/cache/sched-ext-tutorial/target/scx-step-lab/release/scx_oreore --partial -v
```

## スライスを変えたのに起動ログが古い

`make build` だけでは、既定の `STEP=01` をビルドする。
編集した lab を使う場合は `make run STEP=lab MODE=partial` を実行する。
このコマンドには lab のビルドも含まれる。

`slice_ns = 2000000000ULL` は2秒で、起動ログでは `slice=2000000 us` になる。
値が合わなければ、エディタで保存したファイルが `lab/src/bpf/main.bpf.c` かを確認する。
コメントに書いた時間は動作へ影響しないが、数値に合わせて更新しておく。

VM 内のビルドキャッシュよりソースの更新日時が古いと、Cargo が変更前の BPF を再利用することがある。
教材のビルドスクリプトでは C ファイルの内容のハッシュも監視し、更新日時だけに依存せず変更を検知する。

## scheduler が残っている

```console
make reset
```

このコマンドは、教材の scheduler 名と一致した場合だけ `SysRq-S` を送る。
別の `sched_ext` scheduler が動いている場合は、その scheduler の終了手順を使う。

## 実験で遅延が見えない

遅延が観測されないときは、実験の前提が崩れていないかを次の順で確認する。

1. `/sys/kernel/sched_ext/state` が `enabled` になっている
2. `root/ops` が `oreore` で始まっている
3. 負荷生成器が `--sched-ext` 付きで動いている
4. 計算タスクと sleep タスクが `taskset -c 0` で固定されている
5. `STEP=02` の2秒スライスを使っている

前提が揃っていても、ホスト側の停止時間が混ざる場合がある。
数値が一度だけ外れたことを scheduler の効果と断定しない。
