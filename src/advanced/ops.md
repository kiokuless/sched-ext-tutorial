# `sched_ext_ops` の使いどころ

三つの callback だけでも FIFO scheduler は動いた。
方針を増やすと、必要な観測点も増える。

- **`running`**：タスクが CPU 上で実行を始めた時刻や仮想時刻を更新する
- **`stopping`**：消費した CPU 時間を計上し、次回の優先度へ反映する
- **`tick`**：実行中タスクを周期的に検査し、必要ならプリエンプションを要求する
- **`enable` と `disable`**：タスクが `SCHED_EXT` へ出入りするときに状態を初期化または破棄する
- **`init_task` と `exit_task`**：タスクごとの BPF 状態を確保または解放する
- **`cpu_online` と `cpu_offline`**：CPU hotplug に合わせてキューや CPU mask を更新する

すべてを実装しても scheduler が良くなるわけではない。
重みに応じた公平性を扱わない FIFO scheduler なら、`running` と `stopping` で仮想時刻を計算する理由はない。

各 callback の正確なシグネチャは、[Linux 7.0 の sched_ext 文書](https://docs.kernel.org/7.0/scheduler/sched-ext.html)と、ビルド時に使用する scx v1.1.3 の `compat.bpf.h` を参照する。

