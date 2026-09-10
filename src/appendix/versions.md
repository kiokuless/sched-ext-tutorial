# 固定したバージョン

本書では、コードの由来である Linux 6.18、実行対象となる Ubuntu 26.04 の標準カーネル、互換レイヤーを担う scx crates を区別する。
それぞれの版は役割が異なり、次の組み合わせを一単位として検証する。

| 対象 | バージョン |
|---|---|
| Host | Apple Silicon Mac |
| Multipass | 1.16.3以降 |
| Guest | Ubuntu Server 26.04 LTS arm64 |
| Linux | 標準カーネル（検証時は `7.0.0-30-generic`） |
| scx crates | 1.1.3 |
| clang | 19 |
| Rust | 1.95.0 |
| mdBook | 0.5.4 |

`sched_ext` の BPF API には安定性保証がない。
新しい Ubuntu イメージやカーネルへ更新するときは、本文だけを直すのではなく、全 checkpoint のビルドとロード、複数端末での sleep の実験、watchdog による復帰までを一緒に検証する。

実際にインストールされたパッケージの版は、プロビジョニング時に VM の `/etc/sched-ext-tutorial/versions` へ記録される。

## Windows 向け追加手順の検証状況

[Windows 向け手順](../handson/windows.md)は、2026年9月8日に Windows 11 Education（ビルド26200）、Ryzen 7 3800X、MSYS2 の GNU Make 4.4.1、Multipass 1.16.3、Hyper-V、Ubuntu 26.04 amd64、Linux `7.0.0-30-generic` で検証した。
当時の教材に対して Windows ホストで `make vm-up`、`make vm-bootstrap`、`make doctor`、`make restore`、`make build`、`make run`、`make bench`、`make reset`、`make vm-shell` を実行し、共有ソースからのビルド、ロードと解除、15標本の比較実験、watchdog 復帰を確認した。
doctor は `aarch64` と `x86_64` を受け入れるが、検査を通ることだけで実験結果の検証済みとはしない。
上の表と本文の測定例は、引き続き Mac / arm64 での検証記録である。
`make check` は、同じ共有ソースを使い、ビルド成果物を VM 内のファイルシステムに置いて実行し、成功した。
Windows の別エディション、別CPU、別バックエンドまで実機検証済みという意味ではない。

その後に追加した sleep の手動実験、`make bench CASE=dsq`、`make race`、`make team-race` は、Windows での実機検証をまだ行っていない。
