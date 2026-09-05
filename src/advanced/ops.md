# `sched_ext_ops` の使いどころ

本編の scheduler は、三つの callback だけで FIFO を実現した。
三つで足りるのは、順番さえ守れば「どのタスクを、どれだけ動かすか」が決まるからである。
方針を増やすと、それを支える状態と、状態を更新するタイミングが必要になる。
残りの callback は、このタイミングを提供するためのものだ。

- **`running`**：タスクが CPU 上で実行を始めた時刻や仮想時刻を更新する
- **`stopping`**：消費した CPU 時間を計上し、次回の優先度へ反映する
- **`tick`**：実行中タスクを周期的に検査し、必要ならプリエンプションを要求する
- **`enable` と `disable`**：タスクが `SCHED_EXT` へ出入りするときに状態を初期化または破棄する
- **`init_task` と `exit_task`**：タスクごとの BPF 状態を確保または解放する
- **`cpu_online` と `cpu_offline`**：CPU hotplug に合わせてキューや CPU mask を更新する

[観測結果を説明する](../handson/conclusion.md)で触れた「長いスライスを保ちながら起床タスクだけをプリエンプトする」方針は、`tick` で実行中タスクを検査し、プリエンプションを要求する道が開ける。
このように、追加の callback は「やりたい方針」から逆算して選ぶ。
すべてを実装しても scheduler が良くなるわけではない。
重みに応じた公平性を扱わない FIFO scheduler なら、`running` と `stopping` で仮想時刻を計算する理由はない。

なお、`init` と `exit` は本編ですでに使っている。
共有 DSQ の作成に使った `init` と、停止理由を記録した `exit` は、scheduler 全体の寿命に対応する callback である。
一方、`init_task` と `exit_task` はタスクごとの寿命に対応し、粒度が違う。

各 callback の正確なシグネチャは、[Linux 7.0 の sched_ext 文書](https://docs.kernel.org/7.0/scheduler/sched-ext.html)と、ビルド時に使用する scx v1.1.3 の `compat.bpf.h` を参照する。
