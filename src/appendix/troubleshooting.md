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
成功するなら、直前に変更した BPF コードが verifier の制約に反している可能性がある。

`make run STEP=lab MODE=partial` に `-v` を渡したい場合は、VM 内で次を実行する。

```console
sudo /var/cache/sched-ext-tutorial/target/scx-step-lab/release/scx_oreore --partial -v
```

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
4. CPU-bound タスクと周期タスクが `taskset -c 0` で固定されている
5. `STEP=03` の2秒スライスを使っている

前提が揃っていても、ホスト側の停止時間が混ざる場合がある。
数値が一度だけ外れたことを scheduler の効果と断定しない。
