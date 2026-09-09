# 固定したバージョン

この教材は複数の版が絡む。
コードの由来（Linux 6.18）、実行対象（Ubuntu 26.04 の標準カーネル）、互換レイヤー（scx crates）は、それぞれ役割が違う。
この教材は次の組み合わせを一単位として検証する。

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
教材を新しい Ubuntu イメージやカーネルへ更新する場合は、本文だけでなく、全 checkpoint のビルド、ロード、複数端末での sleep の実験、watchdog 復帰までを一緒に検証する。

VM の `/etc/sched-ext-tutorial/versions` には、プロビジョニング時に解決された実際のパッケージ版を記録する。
