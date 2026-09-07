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
教材を新しい Ubuntu イメージやカーネルへ更新する場合は、本文だけでなく、全 checkpoint のビルド、ロード、15 標本の実験、watchdog 復帰までを一緒に検証する。

VM の `/etc/sched-ext-tutorial/versions` には、プロビジョニング時に解決された実際のパッケージ版を記録する。

## Windows 向け追加手順の検証状況

[Windows 向け手順](../handson/windows.md)は、2026年9月7日に Windows 11 Education（ビルド26200）、Ryzen 7 3800X、Multipass 1.16.3、Hyper-V、Ubuntu 26.04 amd64、Linux `7.0.0-30-generic` で検証した。
doctor は `aarch64` と `x86_64` を受け入れるが、検査を通ることだけで実験結果の検証済みとはしない。
上の表と本文の測定例は、引き続き Mac / arm64 での検証記録である。
Windows での全 checkpoint と `lab` のビルド、ロードと解除、15標本の比較実験、watchdog 復帰の結果は、[Windows 向け手順](../handson/windows.md)に記載した。
Windows の別エディション、別CPU、別バックエンドまで実機検証済みという意味ではない。
