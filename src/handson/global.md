# 最小のスケジューラを動かす

前章では、タスクを待ち行列へ入れる判断を BPF 側で書けることを見た。
その判断が入っているのは、数十行の C ファイルである。
実行可能なタスクを組み込みのグローバル DSQ へ入れ、CPU へ渡す処理はカーネルに任せる。
これが、これから動かす最小のスケジューラである。

まず用意されたコードを読み、VM へロードして、一つのタスクを動かす。
動作を確認できたら、タスクに渡すスライスを自分で変更し、変更した値で起動したことを確かめる。
ソースの編集から実行までを一度通しておくと、後で待ち行列の方針を変えたときも、同じ手順で試せる。

## 編集するファイルと完成例

Mac 上で、環境構築のときに取得した `sched-ext-tutorial` ディレクトリを普段のエディタで開く。
端末でも同じディレクトリへ移動する。
以降の `make` コマンドは、VM のシェルではなく、この Mac 側のリポジトリ直下で実行する。
環境構築のときに `make vm-shell` を使って VM に入ったままなら、`exit` で Mac 側へ戻っておく。

編集に使うのは `lab` ディレクトリである。
そこにはスケジューラの方針を書く C ファイルと、それをカーネルへ読み込む Rust プログラムが入っている。
一方、`checkpoints` には、各段階まで完成させたコードを番号ごとに保存してある。

```text
sched-ext-tutorial/
├── lab/
│   └── src/
│       ├── bpf/main.bpf.c   ← スケジューラの方針を書くファイル
│       └── main.rs         ← BPF を読み込む loader
└── checkpoints/
    ├── step-01-global/     ← この章の出発点となる完成例
    ├── step-02-shared-dsq/ ← 共有 DSQ を追加した完成例
    └── …
```

`step-01-global` の最小例を lab へコピーして、編集の出発点を用意する。
すでに `lab/src/bpf/main.bpf.c` を編集している場合は、この操作で上書きされるため、別のファイルへコピーするなどして変更を退避しておく。

```console
make restore STEP=01
```

エディタで `lab/src/bpf/main.bpf.c` を開き、末尾に `SCX_OPS_DEFINE` があることを確かめよう。
以降もこのファイルを編集し、詰まったときには対応する番号の checkpoint と比較する。

## この C ファイルは誰が呼ぶのか

開いたファイルには、C の `main()` がない。
通常の C プログラムなら `main()` から関数を呼んで処理を進めるが、ここに書くのは、カーネルがスケジューリングの途中で呼ぶ関数である。
タスクが実行可能になったときなどに、カーネルが引数を渡して関数を呼び、その戻り値や DSQ への操作を使って処理を続ける。
前章の「callback」は、この呼ばれ方を指している。

ファイルの末尾を見ると、呼び出す場面と関数の対応が書かれている。

```c
SCX_OPS_DEFINE(oreore_ops,
               .select_cpu = (void *)oreore_select_cpu,
               .enqueue    = (void *)oreore_enqueue,
               .exit       = (void *)oreore_exit,
               .timeout_ms = 5000,
               .name       = "oreore");
```

`SCX_OPS_DEFINE` は、関数の対応とスケジューラの設定をまとめるマクロである。
たとえば `.enqueue = (void *)oreore_enqueue` は、「タスクを待ち行列へ入れる判断を求められたら、`oreore_enqueue` を呼ぶ」という登録である。
左側の `enqueue` はカーネルが定めた役割の名前であり、右側の `oreore_enqueue` はこのファイルで定義した関数の名前である。
関数を書くことと、その関数を callback として登録することの両方が必要になる。

同じように、CPU の候補選択には `oreore_select_cpu`、スケジューラの終了時には `oreore_exit` を登録している。
`.name` の `oreore` は、後でロードしたスケジューラを識別するときに使う。
`.timeout_ms` はタスクの停滞を検出するためのタイムアウトであり、[watchdog の章](./watchdog.md)で扱う。

この対応をカーネルへ渡すのが、`lab/src/main.rs` にある Rust の loader である。
loader の起動後、スケジューリングの判断には C 側の関数が使われる。
今回編集する判断がどこにあるかを、`enqueue` から追ってみよう。

## 実行可能なタスクを DSQ へ入れる

ファイルの中央にある `oreore_enqueue` を探す。
この関数に渡されるのは、CPU を使える状態にあり、スケジューラが受け取ったタスクである。
どの待ち行列に置くかを、関数の中で決める。

```c
void BPF_STRUCT_OPS(oreore_enqueue, struct task_struct *p, u64 enq_flags)
{
    scx_bpf_dsq_insert(p, SCX_DSQ_GLOBAL, slice_ns, enq_flags);
}
```

`BPF_STRUCT_OPS` は、カーネルから callback として呼べる形で関数を定義するマクロである。
最初の引数 `oreore_enqueue` が関数名で、その後ろに、この関数が受け取る引数が並んでいる。
`p` は対象のタスクを表す `task_struct` へのポインタである。
`enq_flags` は投入時の条件を表すフラグで、ここでは受け取った値をそのまま次の関数へ渡す。

関数の中で呼んでいる `scx_bpf_dsq_insert()` は、カーネルが BPF プログラムへ公開している関数である。
四つの引数は、次の指定に対応する。

| 引数 | このコードで渡す値 | 指定していること |
|---|---|---|
| 第1引数 | `p` | どのタスクを入れるか |
| 第2引数 | `SCX_DSQ_GLOBAL` | どの DSQ に入れるか |
| 第3引数 | `slice_ns` | どれだけの CPU 時間を割り当てるか |
| 第4引数 | `enq_flags` | どの投入条件を引き継ぐか |

したがって、この一行は「受け取ったタスクを、指定したスライス付きでグローバル DSQ へ入れる」という方針になる。

グローバル DSQ は、あらかじめカーネルが用意している。
CPU は自分のローカル DSQ が空ならグローバル DSQ からタスクを取得できるため、この構成では取り出すための `dispatch` を書かずに済む。
`oreore_enqueue` を登録するだけで受け渡しの経路ができるのは、取り出し側をカーネルが担当しているためである。

## 一度に渡す CPU 時間

`slice_ns` の定義は、ファイルの先頭付近にある。

```c
const volatile u64 slice_ns = 20000000ULL;  /* 20 ms, kernel default */
```

名前の末尾の `ns` はナノ秒を表し、`20000000` ナノ秒は 20 ミリ秒である。
先ほどの `scx_bpf_dsq_insert()` は、この値をスライスとして渡していた。
この変数を変えると、タスクが一度 CPU を得たときに使える時間が変わる。
ただし、タスクが途中で眠ればその時点で CPU を手放すため、毎回 20 ミリ秒間走り続けるという意味ではない。

<details>
<summary>C の型名と設定値の宣言</summary>

`u64` は符号なし64ビット整数で、CPU 番号に使う `s32` は符号付き32ビット整数である。
整数リテラルの末尾の `ULL` は、`unsigned long long` 型を指定する接尾辞である。
スライスを変更するときは、ナノ秒単位の整数を書き、`ULL` を残す。

`slice_ns` は、BPF 側からは読み取り専用の設定値として使う。
一方、loader はロード前にその値を差し替えられる。
この用途で使われるのが `const volatile` という宣言である。

教材の loader は、通常は C ファイルの初期値をそのまま使う。
`--slice-us` を指定した場合だけ、BPF の読み取り専用データ領域（rodata）にある値を上書きする。
この章の `make run` ではそのオプションを指定しないので、C ファイルを編集した結果が使われる。

</details>

## wakeup 時に CPU の候補を選ぶ

タスクが眠っている状態から実行可能になるときには、待ち行列へ入れる前に CPU の候補も選ぶ。
そのために登録していたのが `oreore_select_cpu` である。

```c
s32 BPF_STRUCT_OPS(oreore_select_cpu, struct task_struct *p, s32 prev_cpu,
                   u64 wake_flags)
{
    bool is_idle = false;

    return scx_bpf_select_cpu_dfl(p, prev_cpu, wake_flags, &is_idle);
}
```

この関数も、対象タスク `p` をカーネルから受け取る。
`prev_cpu` は前回動いていた CPU、`wake_flags` は wakeup に関する条件である。
戻り値は候補となる CPU の番号である。

この実装では、自分で CPU を探さず、`scx_bpf_select_cpu_dfl()` に判断を委ねる。
これは `prev_cpu` を起点に、idle な CPU を優先して選ぶ組み込み処理である。
`is_idle` は、idle CPU が見つかったかをこの組み込み処理から受け取る変数である。
この最小例では、CPU の番号だけを戻り値に使い、`is_idle` による分岐はまだ行わない。

CPU の候補が決まると、タスクは先ほどの `enqueue` を通ってグローバル DSQ へ入る。
グローバル DSQ は複数の CPU が参照するので、最終的に実行する CPU が、この関数の返した候補と同じになるとは限らない。
コードの二つの関数を、前章の[グローバル DSQ の経路](./model.md)に対応させて確かめよう。

残る `oreore_exit` は、スケジューラが外された理由を記録する関数である。
先頭の `UEI_DEFINE` と、関数内の `UEI_RECORD` は、その記録を loader へ渡すために使われる。

このスケジューラは、対象タスクを区別せず、一つのグローバル DSQ へ入れ、共通のスライスを渡している。
CPU の候補選択と、グローバル DSQ からタスクを取り出す処理はカーネルに任せている。
一つの FIFO と一定のスライスで CPU を配ることが、この最小例で選んだ方針である。

## ビルドしてロードする

Mac 側で端末を二つ開き、どちらもリポジトリ直下へ移動する。
役割は次のように分け、端末2は一度 VM に入ったら章の最後までそのまま使う。

| 端末 | 作業する場所 | 役割 |
|---|---|---|
| 端末1 | Mac のリポジトリ直下 | ビルドと loader の起動、終了 |
| 端末2 | `make vm-shell` で入る VM 内 | 状態の確認と負荷生成器の実行 |

コードを保存し、端末1でビルドする。

```console
make build STEP=lab
```

`STEP=lab` は、エディタで開いている lab をビルドする指定である。
`STEP=01` とすると checkpoint 側をビルドするため、lab に加えた変更は反映されない。
自分で編集したコードを試すときは `STEP=lab` を使う。

このコマンドは、VM にマウントされたソースを使い、BPF プログラムと Rust の loader を VM 内でビルドする。
ソースを別途コピーする必要はなく、生成された実行ファイルも VM 内で使う。

エラーがなく端末のプロンプトへ戻れば、ビルドは完了している。
まだカーネルへロードしたわけではないので、スケジューラは有効になっていない。
エラーが出た場合は先へ進まず、表示されたファイル名と行を確認する。

続けて、端末1で loader を起動する。

```console
make run STEP=lab MODE=partial
```

`make run` はビルドも行い、その後 VM 内で loader を起動する。
`MODE=partial` では、明示的に `SCHED_EXT` を選んだタスクだけが自作スケジューラの対象になる。
操作に使う shell は通常のスケジューラで動き続ける。

起動に成功すると、loader は次の行を表示する。

```text
scx_oreore started (mode=partial, slice=20000 us)
```

ログのスライスはマイクロ秒単位なので、`20000 us` はソースに書かれていた 20 ミリ秒に対応する。
この後にプロンプトが戻らないのは、loader がスケジューラへの接続を保って待機しているためである。
端末1はそのままにしておく。

端末2で VM のシェルへ入る。

```console
make vm-shell
```

同じ端末2で、状態を読む。

```console
cat /sys/kernel/sched_ext/state
cat /sys/kernel/sched_ext/root/ops
```

`/sys/kernel/sched_ext/` は、カーネルが現在のスケジューラの状態を公開する場所である。
`state` は有効かどうか、`root/ops` は有効なスケジューラの名前を示す。
次のように `enabled` と `oreore` で始まる名前が出れば、ロードを確認できる。

```console
$ cat /sys/kernel/sched_ext/state
enabled
$ cat /sys/kernel/sched_ext/root/ops
oreore_0.1.0_aarch64_unknown_linux_gnu
```

`oreore` は、C ファイルの `.name` に書かれていた文字列である。
scx_utils がバージョンとビルド対象の情報を付加するため、後ろに続く文字列は環境で変わりうる。
先頭の名前をソースと照合すればよい。
起動ログが出ずに終了した場合や、`state` が `enabled` にならない場合は、端末1のエラーを[トラブルシューティング](../appendix/troubleshooting.md)と照らし合わせる。

## 対象タスクを一つ動かす

ロードできたので、今度はこのスケジューラにタスクを渡す。
partial mode では shell が対象外なので、端末を操作できることだけでは自作スケジューラでタスクを動かした確認にならない。
教材の負荷生成器を使って、明示的に対象へ入るタスクを起動する。

端末2で、負荷生成器をビルドする。

```console
cd /workspace/sched-ext-tutorial
./scripts/guest/build-workload.sh
```

続けて、端末2で次を実行する。

```console
sudo /var/cache/sched-ext-tutorial/target/workload/release/sched-ext-workload \
    periodic --samples 3 --sched-ext
```

`periodic` は、1 秒間隔の予定時刻に処理を再開して、その遅れを表示するタスクである。
`--samples 3` で三つの標本を記録し、`--sched-ext` でこのタスク自身を自作スケジューラの対象へ入れる。

タスクが眠ってから再び実行可能になるたびに、読んだ callback がタスクを受け取り、グローバル DSQ を通して CPU へ渡す。
見出しに続いて三つの標本と集計が出て、エラーなくプロンプトへ戻れば、対象タスクの実行を確認できる。
遅延の大小を比較するのは、CPU を使い続ける別のタスクを加える[長いスライスの実験](./long-slice.md)で行う。

## 終了して元のスケジューラへ戻す

負荷生成器が終了しても、端末1の loader は動いたままである。
端末1で `Ctrl+C` を押して終了させる。
loader が保持していた接続が解放され、自作スケジューラが外れる。

端末2で、もう一度状態を読む。

```console
$ cat /sys/kernel/sched_ext/state
disabled
```

`disabled` に戻っていれば、解除まで確認できた。
解除後は `root/ops` がなくなるため、ここでは `state` を確認する。

## 自分で変更した値を反映する

一度動いたコードで、小さな変更を試そう。
エディタで `lab/src/bpf/main.bpf.c` の `slice_ns` を探し、20 ミリ秒から 30 ミリ秒へ変更する。

```c
const volatile u64 slice_ns = 30000000ULL;  /* 30 ms */
```

起動ログの `slice` がどう変わるかを、実行する前にマイクロ秒へ換算してみる。
ファイルを保存したら、端末1で再び起動する。

```console
make run STEP=lab MODE=partial
```

30 ミリ秒なら、次の表示になる。

```text
scx_oreore started (mode=partial, slice=30000 us)
```

`20000 us` のままなら、エディタで保存したか、編集先が lab か、実行時に `STEP=lab` を指定したかを確かめる。
値が変わっていれば、自分で編集した C の設定値が、ビルドと loader を通ってロードされたことを確認できる。

VM に入ったままの端末2で、同じ負荷生成器のコマンドをもう一度実行する。
三つの標本と終了を確認したら、端末1で `Ctrl+C` を押し、端末2で `state` が `disabled` に戻ったことを確かめる。
端末2で `exit` を実行して Mac 側へ戻る。
最後に、C ファイルの値とコメントを 20 ミリ秒の状態へ戻して保存する。

```c
const volatile u64 slice_ns = 20000000ULL;  /* 20 ms, kernel default */
```

ソースを元に戻す操作は、次回のビルドに使う値を戻すものである。
すでにロード中のスケジューラを変更するには、今回のように終了して、ビルドとロードをやり直す必要がある。

## 変更した値がタスクへ渡る場所

起動ログで確かめたのは、変更したスライスが設定へ反映されたことである。
タスクの遅延への影響はまだ評価していない。
実際のタスクへこの値を渡す場所も、ソースで確かめておこう。

この章の実装では、`slice_ns` に設定した値は、どの callback のどの関数呼び出しを通じてタスクへ渡されるだろうか。
`lab/src/bpf/main.bpf.c` を開き、callback の登録と、値を使っている引数を指して説明してみよう。

<details>
<summary>解答とコードの対応</summary>

`enqueue` に登録した `oreore_enqueue` が、`scx_bpf_dsq_insert()` の第3引数に `slice_ns` を渡している。

```c
scx_bpf_dsq_insert(p, SCX_DSQ_GLOBAL, slice_ns, enq_flags);
```

ソースで変更した初期値は、ビルドとロードを経て、この呼び出しからタスクに渡すスライスとして使われる。

</details>

タスクに渡すスライスは変更できたが、待ち行列から取り出す処理は、まだグローバル DSQ の組み込み処理に任せている。
待ち行列も独自の DSQ に変えるなら、誰がそこからタスクを取り出すのだろうか。
[自分の DSQ を作る](./shared-dsq.md)では、カーネルから次のタスクを求められたときに、独自 DSQ からローカル DSQ へタスクを移す処理を実装する。
