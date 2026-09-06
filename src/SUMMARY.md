# 目次

- [はじめに](./introduction.md)

# ハンズオン

- [実験環境を準備する](./handson/environment.md)
- [`sched_ext` が変えるもの](./handson/model.md)
- [最小のスケジューラを動かす](./handson/global.md)
- [自分の DSQ を作る](./handson/shared-dsq.md)
- [1秒後に戻れないタスク](./handson/long-slice.md)
- [スライスを短くする](./handson/short-slice.md)
- [VM 全体を切り替える](./handson/system-wide.md)
- [壊れたスケジューラから戻る](./handson/watchdog.md)
- [観測結果を説明する](./handson/conclusion.md)

# 発展編

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
