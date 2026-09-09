# 実験環境を準備する

実験には、Apple Silicon Mac 上に作る4 vCPUの Ubuntu VM を使う。
Ubuntu 26.04 の標準カーネルで環境を揃え、自作スケジューラの影響を VM 内に限定する。
参加者ごとの CPU 数やカーネルの違いを減らすことで、スケジューラの変更と観測結果を比べやすくする。

## Multipass をインストールする

VM の作成とシェル接続には **Multipass** を使う。
macOS の端末で、Homebrew から Multipass 1.16.3以降を導入する。

```console
brew install --cask multipass
multipass version
```

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

`vm-bootstrap` は、教材のスケジューラをビルドするためのパッケージと crate 依存関係を導入する。
初回は依存関係の取得に時間がかかるため、ハンズオン当日までにこの章を済ませておくことが望ましい。

## 前提を検査する

`make doctor` で、VM が実験に必要な条件を満たしているかを検査する。

```console
make doctor
```

すべての項目が検査を通ることを確認する。
`fail` があれば、ビルドやロード、測定に必要な条件が欠けているため、[トラブルシューティング](../appendix/troubleshooting.md)で原因を確認してから進む。

検査対象と用途は次のとおりである。

| 検査対象 | 実験で必要な理由 |
|---|---|
| CPU アーキテクチャ、vCPU 数 | 教材の実行条件と揃える |
| `CONFIG_SCHED_CLASS_EXT`、`sched_ext` | カーネルに `sched_ext` が組み込まれている必要がある。無効なカーネルではスケジューラをロードできない |
| **BTF** | カーネル内部の型情報。BPF プログラムがカーネルの構造体を安全に参照するために使う |
| clang、cargo | スケジューラをビルドする |
| bpftool、perf | スケジューラやタスクの動作を観測する |

VM のシェルへ入る場合は、次のコマンドを使う。

```console
make vm-shell
```

VM に入れたら、`exit` で Mac 側へ戻っておく。
以降のビルドや起動は、Mac のリポジトリ直下から `make` で指示する。
