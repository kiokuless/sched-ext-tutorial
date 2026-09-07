# Windows で実験環境を準備する

Windows ホストに MSYS2 の Bash と GNU Make を用意し、本文と同じ `make` コマンドで Multipass の Ubuntu VM を操作する。
ソースは Windows 側のエディタで編集し、ビルドと scheduler の実行は VM に任せる。
自作するのは VM 内の Linux CPU scheduler であり、Windows の scheduler を変更するわけではない。
VM は本文と同じ Ubuntu 26.04、4 vCPU、メモリ4 GiB、ディスク20 GiBとする。
検証済みの組み合わせは[固定したバージョン](../appendix/versions.md)に記載している。

## 対象環境

- Intel / AMD の x86_64 CPU を搭載した Windows 11 Pro / Enterprise / Education と Hyper-V
- Multipass 1.16.3以降
- MSYS2 の Bash、GNU Make、Git、diffutils
- VM に4 vCPU、メモリ4 GiB、ディスク20 GiBを割り当てられる空き容量
- インストール時の管理者権限と、イメージ・パッケージ・crate を取得できるインターネット接続

Windows on Arm はこの手順の対象に含めない。
Windows Home では Hyper-V を使うこの構成を利用できない。
Multipass は Windows で VirtualBox バックエンドも提供しているが、この教材での検証は別途必要になる。
バックエンドの要件とインストーラーは [Multipass 公式インストール手順](https://canonical.com/multipass/docs/latest/how-to-guides/install-multipass/)の Windows 欄を参照する。

## Multipass をインストールする

まず PowerShell で、CPU の仮想化機能の状態を確認する。

```powershell
Get-CimInstance Win32_Processor | Select-Object Name, VirtualizationFirmwareEnabled
Get-CimInstance Win32_ComputerSystem | Select-Object HypervisorPresent
```

`HypervisorPresent` が `False` で、`VirtualizationFirmwareEnabled` も `False` なら、PC の説明書に従って UEFI / BIOS で仮想化機能を有効にする。
AMD では `SVM Mode`、Intel では `Intel Virtualization Technology` などの名前で表示される。
続いて Windows の「Windows の機能の有効化または無効化」で Hyper-V を有効にし、要求されたら再起動する。
BIOS 設定後の再起動とは別に、Hyper-V 有効化後にも再起動が必要になることがある。
Windows に戻ったら、`HypervisorPresent` が `True` であることを確認する。
公式の Windows 用インストーラーから Multipass を導入する。
導入後、新しい PowerShell を通常ユーザーとして開き、次を確認する。

```powershell
multipass version
multipass get local.driver
```

バックエンドが `hyperv` であることを確認する。
既存の Multipass を使っている場合は、他の VM を使えなくしないよう、バックエンドを無条件に切り替えない。

## Windows ホストに Bash と make を用意する

[MSYS2](https://www.msys2.org/)をインストールし、スタートメニューから **MSYS2 MSYS** の端末を開く。
ここで使う Bash は Windows ホスト上で動く。
PowerShell、WSL、VM 内の Bash とは別の端末である。

MSYS2 MSYS で更新とツールの導入を行う。

```bash
pacman -Syu
```

更新中に端末を閉じるよう案内された場合は、端末を開き直して `pacman -Syu` を再実行する。
更新が完了したら次を実行する。

```bash
pacman -S --needed make git diffutils
export PATH="$PATH:/c/Program Files/Multipass/bin"
make --version
multipass version
```

`make` は MSYS2 の `make` パッケージを使う。
この教材の Makefile は `/bin/bash` を呼ぶため、Windows 用の make だけを PowerShell に追加しても実行環境は揃わない。
Multipass を標準と異なる場所に導入した場合は、`PATH` に加えるディレクトリをその場所へ変える。
新しい MSYS2 端末でも、同じ `export PATH=...` を実行する。

## リポジトリを取得して VM を作る

以降の `make` コマンドは、**Windows ホストの MSYS2 MSYS 端末**で実行する。
ソースを置きたい Windows 側のディレクトリへ移動してから取得する。
MSYS2 では、たとえば `C:\Users\名前\Documents\GitHub` は `/c/Users/名前/Documents/GitHub` と表す。

```bash
git clone https://github.com/kiokuless/sched-ext-tutorial.git
cd sched-ext-tutorial
```

すでに取得したリポジトリを使う場合は、そのディレクトリへ `cd` する。
`.gitattributes` でテキストの改行を LF に固定している。
既存の作業コピーに CRLF が残っている場合は、編集内容を保存してからエディタで `.sh` ファイルを LF に変更する。

Windows の Multipass は既定でフォルダー共有を無効にしているので、共有機能を有効にする。
この設定は Multipass 全体に適用され、実際に共有するフォルダーは次の `make vm-up` が指定するリポジトリである。

```bash
multipass set local.privileged-mounts=true
multipass list
make vm-up
make vm-bootstrap
make doctor
```

`make vm-up` は `sched-ext-lab` という専用 VM を作り、このリポジトリを VM の `/workspace/sched-ext-tutorial` へマウントする。
同名の VM がある場合は、その VM が教材用であることを確認する。
別名を使う場合は、`export VM_NAME=sched-ext-lab-win` のように設定してから実行し、別の MSYS2 端末でも同じ設定を使う。
停止済みの教材 VM は `make vm-up` で再開できる。

`make vm-bootstrap` は必要なツールと crate 依存関係を用意し、環境チェックと全 checkpoint のビルドを行う。
初回は時間がかかるので、当日までに済ませておく。
`make doctor` の `architecture` は `x86_64`、`vcpus` は `4` が正常である。
`CONFIG_SCHED_CLASS_EXT`、BTF、各ツール、`sched_ext` を含む全項目が `ok` になることを確認する。

## 本文と同じ make コマンドで進める

Windows でも本文のハンズオンで使う `make` コマンドをそのまま実行する。
本文でホスト側の端末と書かれている場所では、MSYS2 MSYS を使う。
ソースの編集には Windows 側の普段のエディタを使い、取得したリポジトリの `lab/src/bpf/main.bpf.c` を開く。
VM 側に別のリポジトリを clone する必要はない。

MSYS2 の端末を二つ開き、どちらもリポジトリ直下へ移動する。
端末2では `make vm-shell` で VM に入る。

| 端末 | 場所 | 用途 |
|---|---|---|
| 端末1 | Windows ホストの MSYS2 MSYS、リポジトリ直下 | ビルド、起動、終了 |
| 端末2 | `make vm-shell` で入った VM 内 | 状態確認とタスク実行 |

端末1で最初のコードを復元し、起動する。
`make restore` は `lab/src/bpf/main.bpf.c` を上書きするため、残したい変更は先に保存する。

```bash
make restore STEP=01
make build STEP=lab
make run STEP=lab MODE=partial
```

端末2で状態を確認する。

```bash
cat /sys/kernel/sched_ext/state
cat /sys/kernel/sched_ext/root/ops
```

`state` が `enabled`、`ops` が `oreore` で始まることを確認する。
本文の出力例にある `aarch64` は、この x86_64 VM では `x86_64` になる。
端末1で `Ctrl+C` を押し、端末2で `state` が `disabled` に戻ることを確認する。
確認を終えた端末2は `exit` で Windows ホストの MSYS2 へ戻す。

この後は[最初のスケジューラを動かす](./global.md)から本文に沿って進める。
`make run STEP=04 MODE=system`、`make run STEP=05 MODE=system`、`make reset` も Windows ホストから実行する。
教材の開発者向けの `make docs` や `make check` には、別途ホスト側に mdBook や Rust などの開発ツールが必要である。

## 測定ログを残す

本文の `mkdir`、パイプ、`tee` も MSYS2 で使える。
標準出力を Windows ホストで保存するので、ログを VM から転送する手順は不要である。

```bash
mkdir -p target/measurements
set -o pipefail
make bench CASE=fair 2>&1 | tee target/measurements/fair.log
```

長いスライスの実験は、本文に従って `lab` を編集した後に実行する。

```bash
make bench CASE=step STEP=lab 2>&1 | tee target/measurements/long.log
```

短いスライスへ編集してから、同じコマンドで保存先だけを変える。

```bash
make bench CASE=step STEP=lab 2>&1 | tee target/measurements/short.log
```

これらのログは Windows 側のリポジトリの `target/measurements/` にある。
Mac の数値との一致ではなく、同じ VM で方針を変えたときの差を比較する。

## 終了と復旧

scheduler が残っている場合は、Windows ホストの別の MSYS2 端末から `make reset` を実行する。
手動で復旧した場合は、watchdog による自動復帰を確認した記録と分ける。
実験が終わり、VM 内の `state` が `disabled` に戻ったことを確認したら、Windows ホストから停止する。

```bash
make vm-stop
```

VM 内の `exit` は接続を終了するだけで、VM は停止しない。

## つまずきやすい点

`make` が見つからない場合は、MSYS2 MSYS で `pacman -S --needed make` を実行したか確認する。
`multipass` が見つからない場合は、上の `export PATH=...` をその端末でも実行する。

`mounts are disabled` と表示された場合は、`multipass set local.privileged-mounts=true` を確認する。
ホストのソースを別の場所へ移動した場合は、教材 VM の共有だけを `multipass umount sched-ext-lab:/workspace/sched-ext-tutorial` で解除し、新しいリポジトリから `make vm-mount` を実行する。
VM 名を変えた場合は、このコマンドの VM 名も変更する。

`bash\r` や `$'\r': command not found` が出た場合は、スクリプトが CRLF で保存されていないか確認する。
`.gitattributes` を維持し、エディタでも LF を選ぶ。

VM 内のパスに `C:/msys64` が付いてしまう場合は、Windows 対応前のスクリプトを使っていないか確認する。
この教材のスクリプトは、ホスト側の共有元だけを Windows 形式へ変換し、Multipass に渡す VM 内のパスの自動変換を抑止している。
詳細は [MSYS2 のパス変換](https://www.msys2.org/docs/filesystem-paths/)を参照する。

VM が起動しない場合は、Hyper-V、CPU の仮想化機能、VM 用の空きメモリを確認し、[Multipass の起動トラブル対処](https://canonical.com/multipass/docs/latest/how-to-guides/troubleshoot/troubleshoot-launch-start-issues/)を参照する。
WSL の Ubuntu と Multipass の Ubuntu は異なる環境なので、本文の実験は `make vm-shell` で入った教材 VM で行う。
その他の問題は[トラブルシューティング](../appendix/troubleshooting.md)を参照する。
