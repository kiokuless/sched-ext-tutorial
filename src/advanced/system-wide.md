# VM 全体へ広げる

本編の partial mode では、明示的に指定した実験用タスクだけが自作スケジューラの対象だった。
system-wide mode では、shell やコンパイラ、通常のバックグラウンドサービスも対象になる。
同じスケジューラの適用範囲を広げ、VM の shell でコマンドを実行できるか確かめる。

## 新たに対象になるタスク

partial mode で fair class に残っていた shell も、system-wide mode では自作スケジューラの方針に従う。
ただし、リアルタイムクラスなど、`sched_ext` の対象外となるタスクは残る。

<figure class="technical-figure">
<div class="diagram-scroll" tabindex="0" role="region" aria-label="partial mode と system-wide mode の適用範囲（横スクロール可能）">
<img src="../images/partial-system-wide.svg" alt="partial では periodic と二つの hog が自作 scheduler に入り、shell とサービスは fair class に残る。system-wide では五つとも自作 scheduler に入る。">
</div>
<figcaption>同じタスクを左右で比較。リアルタイムクラスなど、sched_ext の対象外は省略している。</figcaption>
</figure>

入力を待っていた shell には早く応答してほしい一方、コンパイラには計算を進めてほしい。
偶奇で分類するスケジューラは、こうした処理の目的によらず PID で二つの列へ振り分けるため、その配分が通常の操作にも影響する。

## 10 ミリ秒の方針で操作する

実行中のスケジューラと実験用の負荷を終了しておく。
ここでは条件を揃えるため、[自分の待ち行列から取り出す](../handson/shared-dsq.md)の完成例 `STEP=04` を使う。
PID の偶奇で分けた二つの DSQ を交互に選び、10 ミリ秒のスライスを割り当てる実装である。
lab を上書きする必要はない。

端末1（Mac 側のリポジトリ直下）で起動する。

```console
make run STEP=04 MODE=system
```

`MODE=system` は、対象を VM 内の通常タスクへ広げる指定である。
端末2から VM に入り、スケジューラ名とコマンドの実行を確認する。

```console
make vm-shell
cat /sys/kernel/sched_ext/root/ops
uname -a
```

名前が `oreore` で始まり、`uname -a` の出力が返ることを確認する。
そのまま短いコマンドをいくつか実行し、入力から出力までに引っかかりを感じるか観察する。

この操作で確認するのは、自作の方針のもとで shell がコマンドを実行し、出力を返すことまでである。
一度動いただけでは、高い負荷でも快適に使えるとは判断できない。
数値で評価する場合は、入力への応答時間、ビルド時間、throughput などを別々に測る。

## 元へ戻す

端末1で `Ctrl+C` を押す。
端末2で状態を読み、`disabled` に戻ったことを確認してから Mac 側へ戻る。

```console
cat /sys/kernel/sched_ext/state
exit
```

操作できない場合に限り、Mac 側の別の端末から `make reset` を実行する。
対象を広げた影響として、shell を操作した印象を、本編で測った sleep の時間とは分けて記録する。
