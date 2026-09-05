# VM 全体を切り替える

これまでの実験は partial mode で行い、実験対象のタスクだけが自作 scheduler に入っていた。
同じ BPF コードでも、適用対象が変われば影響範囲が変わる。
VM 全体を切り替えると、shell、コンパイラ、バックグラウンドサービスも同じ方針で動く。
partial mode で安全に見えた方針が、system-wide mode でも使いやすいとは限らない。

短いスライスの checkpoint を system-wide mode で起動する。

```console
make run STEP=04 MODE=system
```

別の端末で scheduler 名を確認し、短いコンパイルやコマンドを実行する。

```console
make vm-shell
cat /sys/kernel/sched_ext/root/ops
uname -a
```

観るべきは、10ミリ秒のスライスが対話的な操作にどう感じられるかである。
実験対象を絞っていた partial mode では知りようのない、scheduler 全体としての使い心地が初めて手に入る。

終了するときは scheduler を実行している端末で `Ctrl+C` を押す。
操作できない場合に限り、別の端末から `make reset` を実行する。
`make reset` の安全機構は、次章で実際に頼ることになる。
