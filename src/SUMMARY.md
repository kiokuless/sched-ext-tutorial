# 目次

[はじめに](./introduction.md)

# ハンズオン

- [実験環境を準備する](./handson/environment.md)
- [最初のスケジューラを動かす](./handson/global.md)
- [1秒後に戻れないタスク](./handson/long-slice.md)
- [最初の main.bpf.c を読む](./handson/model.md)
- [A を B の2倍の速さで進める](./handson/race.md)
- [自分の待ち行列から取り出す](./handson/shared-dsq.md)
- [A が増えても B の速さを保つ](./handson/team-race.md)
- [次の方針を選ぶ](./handson/conclusion.md)

# 発展編

- [VM 全体へ広げる](./advanced/system-wide.md)
- [壊して、戻る](./advanced/watchdog.md)
- [`sched_ext_ops` の使いどころ](./advanced/ops.md)
- [CPU ごとの DSQ](./advanced/per-cpu-dsq.md)
- [tail latency の測り方](./advanced/tail-latency.md)
- [Rust で方針を書く](./advanced/rustland.md)
- [実機で評価する](./advanced/bare-metal.md)

# 付録

- [用語集](./appendix/glossary.md)
- [トラブルシューティング](./appendix/troubleshooting.md)
- [固定したバージョン](./appendix/versions.md)
- [ライセンスと由来](./appendix/licenses.md)
