# 用語集

本文で定義した用語を、引き直し用にまとめる。
初出の章で意味と使い方を説明しているため、ここでは短い定義だけを載せる。

## スケジューリング

- **スケジューラ（scheduler）**：実行可能なタスクへ CPU をどう割り当てるかを決める仕組み、またはその実装。本書では文脈に応じて Linux の標準スケジューラと自作の BPF scheduler を区別して書く。
- **fair class**：通常の Linux タスクを公平に扱う標準の scheduling class。本編では自作 `sched_ext` scheduler と比較する基準として使う。
- **タスク**：カーネルがスケジューリングする実行単位。本編ではユーザ空間から見た説明では「プロセス」と書く場合もある。
- **runnable**：実行可能で、CPU を得れば命令を実行できる状態。
- **wakeup**：I/O やタイマーなどの待ち状態にあったタスクが、再び実行可能になる状態変化。
- **タイムスライス**：タスクが CPU 上で連続して実行できる時間の割り当て。
- **コンテキストスイッチ**：CPU 上で実行するタスクを別のタスクへ切り替えること。
- **CPU-bound**：実行時間の多くを CPU 計算に使う workload。
- **hog**：本編で CPU を使い続ける負荷タスクに付けた呼び名。負荷生成器の `cpu-hog` を二つ起動し、hog A と hog B と呼ぶ。
- **periodic**：負荷生成器の周期タスク。予定時刻ごとに処理を再開し、その時刻からの遅れを記録する。
- **idle**：CPU に実行するタスクがなく、空いている状態。
- **プリエンプション**：実行中のタスクに、スライスの終了を待たず CPU を譲らせること。
- **deadline miss**：予定時刻からの遅れが、実験で決めた許容値を超えたこと。
- **CPU affinity**：タスクが実行できる CPU を制限する設定。本編では `taskset` で設定する。

## `sched_ext`

- **`sched_ext`**：BPF プログラムで CPU scheduling policy を実装し、実行時にロードできる Linux の extensible scheduler class。
- **`sched_ext_ops`**：BPF scheduler の callback と設定をまとめてカーネルへ渡す構造体。
- **DSQ（dispatch queue）**：`sched_ext` がタスクを CPU へ渡すために使う待ち行列。
- **ローカル DSQ**：各 CPU が持つ DSQ。CPU は最終的に自分のローカル DSQ からタスクを実行する。
- **グローバル DSQ**：カーネルが用意する、CPU 間で共有される DSQ。
- **独自 DSQ**：BPF scheduler が作成して管理する DSQ。
- **`SCHED_EXT`**：タスクが `sched_ext` の対象になるために選べる scheduling policy。
- **partial switching**：`SCX_OPS_SWITCH_PARTIAL` を使い、明示的に `SCHED_EXT` を選んだタスクだけを BPF scheduler の対象にする使い方。
- **watchdog（stall detection）**：BPF scheduler が runnable task を長時間進められないなどの異常を検出し、scheduler を abort して標準の scheduling へ戻す仕組み。
- **SysRq-S**：動作中の `sched_ext` BPF scheduler を停止し、標準の scheduling へ戻すための SysRq 操作。

## BPF と loader

- **BPF**：カーネル内の決められた実行点で動かせる、ロード時に検証されるプログラムの仕組み。
- **BPF verifier**：BPF プログラムをカーネルへロードする前に、許されない動作などがないか検査する仕組み。
- **BTF**：カーネルや BPF プログラムの型情報を表現する仕組み。本編では BPF 側からカーネルの型を扱うために利用する。
- **loader**：BPF object を開き、設定値を与え、カーネルへ load、attach するユーザ空間プログラム。本編では Rust で実装されている。
- **rodata**：BPF object の読み取り専用データ領域。本編では loader が load 前に `slice_ns` などの初期値を設定するために使う。
- **`const volatile`**：BPF のグローバル設定値でよく使われる宣言。本編では「BPF 側では読み取り専用として使い、loader が load 前に初期値を与える」ための定型的な書き方として扱う。
- **`uei_report`**：scheduler の exit 情報を loader 側で整形して表示するための補助。

## 観測

- **p50、p95、p99**：遅延を小さい順に並べたときの50、95、99パーセンタイル。
- **tail latency**：遅延分布の上位側にある遅い部分。p95、p99、p99.9 など高いパーセンタイルで観測することが多い。
- **throughput**：単位時間あたりに完了した仕事量。本編の遅延と切り替え回数だけでは判断できない。
- **Perfetto trace**：イベントを時系列で可視化できる trace 形式。発展編では `scxtop` からの出力先として扱う。
- **NUMA**：CPU とメモリの距離が一様ではないハードウェア構成。実機で locality を評価するときに重要になる。
