# Rust で方針を書く

本編の構成は、[scheduler を載せる仕組み](../handson/model.md)で示した loader の流れそのものであった。
スケジューリングの判断は BPF C に置かれ、Rust プログラムは BPF object をロードするだけだった。
BPF 内で使えるデータ構造と処理には制約がある。
複雑なキュー操作を BPF C の中で書くのが難しい場合、判断そのものをユーザー空間へ移すという選択肢がある。
`scx_rustland_core` は、BPF との受け渡しを抽象化し、その構成を作りやすくする。

公式の [`scx_rustland`](https://github.com/sched-ext/scx/tree/v1.1.3/scheds/rust/scx_rustland) は、ユーザー空間で方針を実装するためのテンプレートである。
タスクを dequeue し、Rust のデータ構造で順序を決め、CPU とスライスを指定して dispatch できる。

ただし、ユーザー空間 scheduler は BPF 内で判断を完結させる scheduler と同じではない。
タスク情報をユーザー空間へ渡して判断を返す経路が増えるため、scheduler 自身が十分な頻度で実行できることも設計条件になる。
判断の主体が loader プロセスになるため、「loader の生存期間だけ scheduler が有効」という関係も、本編より強く出る。
