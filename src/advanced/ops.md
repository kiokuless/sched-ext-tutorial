# `sched_ext_ops` の使いどころ

本編の scheduling path は、`select_cpu`、`enqueue`、`dispatch` と固定のスライスで FIFO を実現した。
初期化と終了には、別に `init` と `exit` を使った。
方針を増やすと、それを支える状態と、状態を更新するタイミングが必要になる。
残りの callback は、このタイミングを提供するためのものだ。

- **`running`**：タスクが CPU 上で実行を始めた時刻や仮想時刻を更新する
- **`stopping`**：消費した CPU 時間を計上し、次回の優先度へ反映する
- **`tick`**：実行中タスクを周期的に検査し、必要ならプリエンプションを要求する
- **`enable` と `disable`**：タスクが `SCHED_EXT` へ出入りするときに状態を初期化または破棄する
- **`init_task` と `exit_task`**：タスクごとの BPF 状態を確保または解放する
- **`cpu_online` と `cpu_offline`**：CPU hotplug に合わせてキューや CPU mask を更新する

[次の方針を選ぶ](../handson/conclusion.md)の「長いスライスを保ちながら、wakeup したタスクへ早く CPU を渡す」方針では、待っているタスクを記録する状態と、実行中のタスクに CPU を譲らせる仕組みが必要になる。
`tick` でその状態を周期的に確認する設計も考えられるが、wakeup した瞬間に反応する処理とはタイミングが異なる。
このように、追加の callback は「やりたい方針」から逆算して選ぶ。
すべてを実装しても scheduler が良くなるわけではない。
重みに応じた公平性を扱わない FIFO scheduler なら、`running` と `stopping` で仮想時刻を計算する理由はない。

なお、`init` と `exit` は本編ですでに使っている。
共有 DSQ の作成に使った `init` と、停止理由を記録した `exit` は、scheduler 全体の寿命に対応する callback である。
一方、`init_task` と `exit_task` はタスクごとの寿命に対応し、粒度が違う。

各 callback の正確なシグネチャは、Linux 7.0 の `sched_ext` 文書と、ビルド時に使用する scx v1.1.3 の `compat.bpf.h` を参照する。
