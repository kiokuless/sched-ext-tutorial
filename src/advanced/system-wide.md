# VM 全体へ広げる

本編の partial mode では、明示的に指定した実験用タスクだけが自作スケジューラの対象だった。
system-wide mode では、shell やコンパイラ、通常のバックグラウンドサービスも対象になる。
同じスケジューラの適用範囲を広げ、VM の shell を実際に操作できるかを確かめる。

## 新たに対象になるタスク

partial mode で fair class に残っていた shell も、system-wide mode では自作スケジューラの方針に従う。
リアルタイムクラスなど、`sched_ext` の対象外となるタスクは残る。

<figure class="technical-figure">
<div class="diagram-scroll" tabindex="0" role="region" aria-label="partial mode と system-wide mode の適用範囲（横スクロール可能）">
<img src="../images/partial-system-wide.svg" alt="partial では periodic と二つの hog が自作 scheduler に入り、shell とサービスは fair class に残る。system-wide では五つとも自作 scheduler に入る。">
</div>
<figcaption>同じタスクを左右で比較。リアルタイムクラスなど、sched_ext の対象外は省略している。</figcaption>
</figure>

入力を待っていた shell には早く応答してほしい一方、コンパイラには計算を進めてほしい。
偶奇で分類するスケジューラでは、どちらも処理の目的によらず PID の偶奇で二つの列へ振り分けられるため、通常の操作にもその配分が影響する。

## 10 ミリ秒の方針で操作する

実行中のスケジューラと実験用の負荷が終了していることを確認する。
ここでは条件を揃えるため、[自分の待ち行列から取り出す](../handson/shared-dsq.md)で使った完成例 `STEP=04` を使う。
PID の偶奇で分けた二つの DSQ を交互に選び、スライスを 10 ミリ秒にしたものである。
lab を上書きする操作は必要ない。

端末1（Mac 側のリポジトリ直下）で起動する。

```console
make run STEP=04 MODE=system
```

`MODE=system` が、対象を VM 内の通常タスクへ広げる指定である。
端末2から VM に入り、スケジューラ名を確認する。

```console
make vm-shell
cat /sys/kernel/sched_ext/root/ops
uname -a
```

名前が `oreore` で始まることと、コマンドの出力が返ることを確かめる。
そのまま短いコマンドをいくつか実行し、入力から出力までに引っかかりを感じるかを見てみる。

コマンドが一度動いただけでは、負荷が高くても快適に使えるとは判断できない。
この操作で確認する範囲は、自作の方針のもとで shell がコマンドを実行し、出力を返すことまでである。
数値で評価するなら、入力への応答時間、ビルドにかかった時間、throughput などを別々に測る。

## 元へ戻す

端末1で `Ctrl+C` を押し、端末2で状態を確認する。

```console
cat /sys/kernel/sched_ext/state
exit
```

`disabled` に戻れば解除できている。
操作できない場合に限り、Mac 側の別の端末から `make reset` を実行する。

対象タスクを広げた影響を記録するため、shell を操作した印象は、本編で測った sleep の時間と分けて残す。
