# Linux上で動くオレオレCPUスケジューラを作ろう

Linux の `sched_ext` を使い、BPF で小さな CPU scheduler を作るハンズオン教材である。
長いタイムスライスで周期タスクを意図的に遅らせ、スライスを短くしたときの遅延とコンテキストスイッチ数を比較する。

最初のスケジューラを起動して終了するところから始め、スライスの変更とコードの読解を経て、2つの課題へ取り組んでもらう。
各変更の前に、図やコードから結果を一つ予想し、直後の説明や実行結果で確かめる構成としている。

教材は Apple Silicon Mac と4 vCPUの Multipass VM を正式な実行環境とする。
Windows では、[MSYS2 から同じ make コマンドで進める手順](src/handson/windows.md)を使う。
Windows 11 Education / Ryzen 7 3800X / Hyper-V で、ホストからの VM 操作、ビルド、ロードと解除、遅延比較、watchdog 復帰を検証した。
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

名前付きの二つの計算プロセスを動かす課題は、[A を B の2倍の速さで進める](src/handson/race.md)にある。
どちらも同じ量の計算を行い、名前、PID、進捗と毎秒の速度を表示する。

```console
make race STEP=03
# lab のスケジューラを変更してから再実行
make race STEP=lab
```

偶数 PID の三つと奇数 PID の一つを CPU 0 で動かし、単一 FIFO と二つの DSQ の配分を比較する実験は、スケジューラを停止した状態から実行する。

```console
make bench CASE=dsq STEP=03
make bench CASE=dsq STEP=04
```

共有 DSQ を使う課題は、[A が増えても B の速さを保つ](src/handson/team-race.md)にある。
A1 と B1 を動かした後に A2 と A3 を追加し、追加前後の B1 の速度を比較する。

```console
make team-race STEP=03
# lab のスケジューラを変更してから再実行
make team-race STEP=lab
# A の人数を増やして同じ規則を試す
make team-race STEP=lab TEAM_A_MEMBERS=5
```

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
- Linux kernel のサンプルを基にした `lab/`、`checkpoints/`、`solutions/` は GPL-2.0-only で提供する。

由来と個別の範囲は[ライセンスと由来](src/appendix/licenses.md)に記載している。
