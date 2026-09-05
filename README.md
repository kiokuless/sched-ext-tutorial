# Linux上で動くオレオレCPUスケジューラを作ろう

Linux の `sched_ext` を使い、BPF で小さな CPU scheduler を作るハンズオン教材である。
長いタイムスライスで周期タスクを意図的に遅らせ、スライスを短くしたときの遅延とコンテキストスイッチ数を比較する。

教材は Apple Silicon Mac と4 vCPUの Multipass VM を正式な実行環境とする。
本文のソースは `src/`、編集する scheduler は `lab/`、動作する各段階は `checkpoints/` に置いている。

## 本文を読む

mdBook 0.5.4を導入し、次のコマンドを実行する。

```console
mdbook serve --open
```

静的 HTML は `make docs` で `book/` に生成できる。

## ハンズオン環境を作る

macOS に Multipass 1.16.3以降を導入してから、次のコマンドを実行する。

```console
make vm-up
make vm-bootstrap
make doctor
```

標準の Ubuntu 26.04 LTS イメージから VM を作成し、必要なパッケージを導入する。
初回の `vm-bootstrap` は crate 依存関係の取得にやや時間がかかる。

環境が整った後は、たとえば次のコマンドで最初の scheduler をビルドして起動できる。

```console
make build STEP=01
make run STEP=01 MODE=partial
```

詳しい手順は[実験環境を準備する](src/handson/environment.md)から始める。

## 検査する

ホスト側で実行できる検査は次の一つにまとめている。

```console
make check
```

Linux 固有の scheduler build を含む checkpoint の検査は、準備済み VM 上で実行する。

```console
make verify-checkpoints
```

## ライセンス

- `src/` の本文は [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) で提供する。
- 独自のツールとスクリプトは MIT OR Apache-2.0で提供する。
- Linux kernel のサンプルを基にした `lab/` と `checkpoints/` は GPL-2.0-only で提供する。

由来と個別の範囲は[ライセンスと由来](src/appendix/licenses.md)に記載している。
