# 実験環境を準備する

実験結果を比べるには、参加者ごとの CPU 数とカーネルを揃える必要がある。
この教材では、Apple Silicon Mac 上に4 vCPUの Ubuntu VM を作り、Ubuntu 26.04 の標準カーネルを使う。

## Multipass をインストールする

macOS では Homebrew から Multipass を導入できる。

```console
brew install --cask multipass
multipass version
```

Multipass 1.16.3以降を使う。

## リポジトリを取得する

```console
git clone https://github.com/kiokuless/sched-ext-tutorial.git
cd sched-ext-tutorial
```

Mac 上のこのディレクトリが VM の `/workspace/sched-ext-tutorial` にマウントされる。
ソースは普段のエディタで編集し、Linux が必要なビルドと実行だけを VM に任せる。

## VM を起動する

```console
make vm-up
make vm-bootstrap
```

`vm-bootstrap` は必要なパッケージと crate 依存関係を導入する。
完了した時点で、VM はすべての scheduler をビルドできる状態になる。

## 前提を検査する

```console
make doctor
```

検査対象は、CPU アーキテクチャ、vCPU 数、`CONFIG_SCHED_CLASS_EXT`、BTF、clang、cargo、bpftool、perf、`sched_ext` である。
一つでも `fail` になった状態では、後の観測値を比較できない。

VM のシェルへ入る場合は、次のコマンドを使う。

```console
make vm-shell
```
