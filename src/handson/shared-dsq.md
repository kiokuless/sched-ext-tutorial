# 自分の DSQ を作る

前章の scheduler は動いたが、タスクをグローバル DSQ へ入れたあとのことは、カーネルが取り仕切っていた。
CPU がグローバル DSQ から直接タスクを取るため、いつ、どの CPU へ渡すかを scheduler が制御する余地がない。
自分で DSQ を作ると、出し時と行き先が callback の仕事になる。

ここで一つ疑問が生まれる。
前章の scheduler もタスクを実行できていたのに、なぜわざわざ自分の DSQ を作る必要があるのだろうか。
動かすだけなら、組み込みのグローバル DSQ で十分である。
それでも自分のキューを持つのは、待たせ方そのものを scheduler の方針にしたいからである。

CPU scheduler を作るというと、実行するタスクを選ぶ複雑な判定式を書くことを想像しやすい。
しかし、多くのスケジューリング方針は「どの待ち行列へ入れるか」「どの順番で取り出すか」「どの CPU にその列を担当させるか」というキューの設計として表現できる。
到着順に並べれば FIFO になり、優先度を持たせれば重要なタスクを先に出せる。
CPU ごとにキューを分ければ、前回動いた CPU やキャッシュの再利用を意識した方針も作れる。

この章で共有 DSQ を一つ作るのは、その最小形である。
アルゴリズム自体はまだ単純な FIFO のままだが、待ち行列の所有者がカーネルの組み込み処理から自分の scheduler へ移る。
見た目の挙動が前章とほとんど同じでも、この境界を越えることで、次章から「いつ CPU に渡すか」を実験対象にできる。

```console
make restore STEP=02
```

## idle CPU への直接 dispatch

前章で読み飛ばした `is_idle` が、ここで出番になる。
`select_cpu` が idle CPU を見つけた場合は、その CPU のローカル DSQ へ直接タスクを入れる。

```c
cpu = scx_bpf_select_cpu_dfl(p, prev_cpu, wake_flags, &is_idle);
if (is_idle)
    scx_bpf_dsq_insert(p, SCX_DSQ_LOCAL, slice_ns, 0);
```

ローカル DSQ へ直接入れたタスクは、`enqueue` を経由しない。
空いている CPU があるのに共有の待ち行列で順番を待つのは無駄だから、scheduler が先回りして判断している。
待ち行列を一段飛ばせる、というのがこの処理の意味である。

## 共有 DSQ から CPU へ渡す

idle CPU へ直接渡せなかったタスクは、ID 0の共有 DSQ に入れる。

```c
#define SHARED_DSQ 0

void BPF_STRUCT_OPS(oreore_enqueue, struct task_struct *p, u64 enq_flags)
{
    scx_bpf_dsq_insert(p, SHARED_DSQ, slice_ns, enq_flags);
}
```

DSQ の ID は scheduler が自由に選べる `u64` であり、ここでは 0 を `SHARED_DSQ` という名前にした。

CPU が仕事を求めると `dispatch` が呼ばれる。
`scx_bpf_dsq_move_to_local()` は共有 DSQ の先頭を、呼び出し元 CPU のローカル DSQ へ移す。

```c
void BPF_STRUCT_OPS(oreore_dispatch, s32 cpu, struct task_struct *prev)
{
    scx_bpf_dsq_move_to_local(SHARED_DSQ, 0);
}
```

## DSQ の作成

独自 DSQ は、scheduler の初期化時に作成する。

```c
s32 BPF_STRUCT_OPS_SLEEPABLE(oreore_init)
{
    return scx_bpf_create_dsq(SHARED_DSQ, -1);
}
```

`BPF_STRUCT_OPS_SLEEPABLE` は、睡眠できる context で呼ばれる callback を示す。
DSQ の作成のような処理はここに置く。
`scx_bpf_create_dsq` の第2引数は、DSQ のメモリを割り当てる NUMA node の指定であり、-1 は指定しないことを意味する。

これで、前章の図にあった経路がすべて自前の実装になった。
`enqueue` が共有 DSQ に入れ、`dispatch` がそれをローカル DSQ へ移す。

`make build STEP=lab` と `make run STEP=lab MODE=partial` で動作を確認する。
動きそのものは前章と変わって見えないはずである。
「いつタスクを出すか」の判断を組み込みの処理から自前の callback へ移したのがこの章であり、その差が数値として現れるのは次章以降である。
詰まった場合は `checkpoints/step-02-shared-dsq/` と比較できる。
