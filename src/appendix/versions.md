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
