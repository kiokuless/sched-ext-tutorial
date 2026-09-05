# Rust で方針を書く

本編の Rust プログラムは BPF オブジェクトをロードするだけであり、スケジューリング判断は BPF C に置かれていた。
複雑なキュー操作を Rust で試したい場合は、`scx_rustland_core` が BPF との受け渡しを抽象化する。

公式の [`scx_rustland`](https://github.com/sched-ext/scx/tree/v1.1.3/scheds/rust/scx_rustland) は、ユーザー空間で方針を実装するためのテンプレートである。
タスクを dequeue し、Rust のデータ構造で順序を決め、CPU とスライスを指定して dispatch できる。

ただし、ユーザー空間 scheduler は BPF 内で判断を完結させる scheduler と同じではない。
タスク情報をユーザー空間へ渡して判断を返す経路が増えるため、scheduler 自身が十分な頻度で実行できることも設計条件になる。

