# 実験環境を準備する

この本の実験は、スケジューラの設定を変えたときの遅延の差を数値で比較する。
比較が成立するには、CPU 数とカーネルが参加者間で揃っている必要がある。
そこでこの教材では、実行環境そのものを固定し、Apple Silicon Mac 上に4 vCPUの Ubuntu VM を作り、Ubuntu 26.04 の標準カーネルを使う。
VM を使う理由は再現性のほかに安全があるが、その詳細ははじめにの「実行上の注意」に譲る。

## Multipass をインストールする

macOS では Homebrew から Multipass を導入できる。
Multipass はコマンド一つで Ubuntu VM を作成・操作できるツールで、この本では VM の作成とシェル接続に使う。

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
ソースは普段のエディタで編集し、Linux でないと動かないビルドと実行だけを VM に任せる。

## VM を起動する

```console
make vm-up
make vm-bootstrap
```

`vm-bootstrap` は必要なパッケージと crate 依存関係を導入する。
完了した時点で、VM はすべての scheduler をビルドできる状態になる。
初回は依存関係の取得に時間がかかるため、ハンズオン当日までにこの章を済ませておくことが望ましい。

## 前提を検査する

環境を固定したつもりでも、想定と違う状態で VM が立っていることはある。
そこで `make doctor` が、後続の実験に必要な前提を一括で検査する。

```console
make doctor
```

検査対象は、CPU アーキテクチャ、vCPU 数、`CONFIG_SCHED_CLASS_EXT`、BTF、clang、cargo、bpftool、perf、`sched_ext` である。
このうち `CONFIG_SCHED_CLASS_EXT` は、カーネルに `sched_ext` が組み込まれているかを示す設定であり、無効なカーネルではそもそも scheduler をロードできない。
BTF はカーネル内部の型情報で、BPF プログラムがカーネルの構造体を安全に参照するために必要になる。
clang と cargo は scheduler のビルドに、bpftool と perf は観測に使う。
一つでも `fail` になった状態では、後の観測値を比較できない。

VM のシェルへ入る場合は、次のコマンドを使う。

```console
make vm-shell
```
