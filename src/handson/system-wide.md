# VM 全体を切り替える

partial switching では、実験対象だけが `SCHED_EXT` に入っていた。
VM 全体を切り替えると、shell、コンパイラ、バックグラウンドサービスも同じ方針で動く。

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

同じ BPF コードでも、適用対象が変われば影響範囲が変わる。
partial mode で安全に見えた方針が、system-wide mode でも使いやすいとは限らない。

終了するときは scheduler を実行している端末で `Ctrl+C` を押す。
操作できない場合に限り、別の端末から `make reset` を実行する。

