# Windows で実験環境を準備する

Windows から Multipass の Ubuntu VM を起動し、その中でソースの編集、ビルド、実験を行う。
自作するのは VM 内の Linux CPU scheduler であり、Windows の scheduler を変更するわけではない。
VM は本文と同じ Ubuntu 26.04、4 vCPU、メモリ4 GiB、ディスク20 GiBとする。

> 2026年9月7日に Windows 11 Education / Ryzen 7 3800X / Hyper-V で、全 checkpoint と `lab` のビルド、ロードと解除、15標本の比較実験、watchdog の自動復帰を確認した。
> 本文の測定値は Apple Silicon Mac 上の arm64 VM で得たもので、Windows 上の amd64 VM で同じ値になるとは限らない。

## 対象環境

- Intel / AMD の x86_64 CPU を搭載した Windows 11 Pro / Enterprise / Education と Hyper-V
- Multipass 1.16.3以降
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

## 実験用 VM を作る

**PowerShell** で実行する。

```powershell
multipass list
multipass launch 26.04 --name sched-ext-lab-win --cpus 4 --memory 4G --disk 20G
multipass shell sched-ext-lab-win
```

`sched-ext-lab-win` は、このハンズオン専用の VM 名である。
同名の VM がすでにある場合は用途を確認し、他の作業用なら別の名前を選んで以降のコマンドも読み替える。
このハンズオン用に作成済みの VM を再開する場合は、`launch` の代わりに `multipass start sched-ext-lab-win` を使う。

ここからプロンプトが `ubuntu@...` に変わり、**VM 内の Bash** になる。
以降、PowerShell と書かれていないコマンドは、この VM 内で実行する。

## ソースとツールを準備する

ソースは VM の Linux ファイルシステムへ直接取得する。
この構成では Windows 側に Git、Bash、make を導入する必要はない。
Windows と VM のフォルダー共有も必要ない。

```bash
sudo apt-get update
sudo apt-get install -y git nano
git clone https://github.com/kiokuless/sched-ext-tutorial.git
cd ~/sched-ext-tutorial
sudo ./vm/provision.sh
```

最後のコマンドが成功したら、次を順番に実行する。
途中で失敗した場合は、その原因を解消してから次へ進む。

```bash
./scripts/guest/doctor.sh
./scripts/guest/verify-checkpoints.sh
./scripts/guest/build-step.sh lab
```

`provision.sh` は、コンパイラー、カーネルに対応する perf、Rust と crate 依存関係を用意する。
`verify-checkpoints.sh` は全 checkpoint と負荷生成器をビルドする。
最後のコマンドで編集用 `lab` もビルドする。
初回は時間がかかるので、当日までにここまでを済ませる。

doctor の `architecture` は `x86_64`、`vcpus` は `4` が正常である。
`CONFIG_SCHED_CLASS_EXT`、BTF、各ツール、`sched_ext` を含む全項目が `ok` になることを確認する。
`expected aarch64, got x86_64` と表示される場合は Windows 対応前のソースを使っているため、この章と対になる doctor の修正を含む版を取得する。
CPU の検査行を削除して他の失敗まで見逃さないようにする。

## 本文のコマンドを読み替える

本文の `make` は、Mac から VM へ処理を送るための入口である。
Windows 版では VM 内から同じスクリプトを直接呼び出す。
VM 内で既存の `make build` や `make vm-up` を実行すると、VM の中からさらに Multipass を呼ぼうとするため、この表を使う。

次の表の右列は、**VM 内の `~/sched-ext-tutorial`** で実行する。
`STEP`、`MODE`、`CASE` の値を変更する場面では、対応する引数を変更する。
たとえば `STEP=lab` は `lab`、`STEP=04` は `04` と書く。

| 本文のコマンド | VM 内で実行するコマンド |
|---|---|
| `make doctor` | `./scripts/guest/doctor.sh` |
| `make verify-checkpoints` | `./scripts/guest/verify-checkpoints.sh` |
| `make restore STEP=01` | `./scripts/restore-step.sh 01` |
| `make build STEP=lab` | `./scripts/guest/build-step.sh lab` |
| `make run STEP=lab MODE=partial` | `./scripts/guest/run-step.sh lab partial` |
| `make run STEP=04 MODE=system` | `./scripts/guest/run-step.sh 04 system` |
| `make run STEP=05 MODE=system` | `./scripts/guest/run-step.sh 05 system` |
| `make bench CASE=fair` | `./scripts/guest/bench.sh fair 01` |
| `make bench CASE=step STEP=lab` | `./scripts/guest/bench.sh step lab` |
| `make reset` | `./scripts/guest/reset.sh` |

`fair` の場合も第2引数が必要なので `01` を渡すが、この場合 scheduler はロードされない。
`restore` は編集中の `lab/src/bpf/main.bpf.c` を上書きするため、残したい変更は先に保存する。

## 端末を二つ開いて最初の scheduler を動かす

端末1は、準備に使った VM 内の Bash をそのまま使う。
もう一つ PowerShell のタブを開き、端末2として接続する。

```powershell
multipass shell sched-ext-lab-win
```

端末2でも、VM 内で次を実行する。

```bash
cd ~/sched-ext-tutorial
```

| 端末 | Windows 版での場所 | 用途 |
|---|---|---|
| 端末1 | VM 内の `~/sched-ext-tutorial` | ソース編集、ビルド、起動、終了 |
| 端末2 | 同じ VM 内 | 状態の確認、タスク実行、復旧 |

端末1で最初のコードを復元し、ロードする。

```bash
./scripts/restore-step.sh 01
./scripts/guest/run-step.sh lab partial
```

端末2で確認する。

```bash
cat /sys/kernel/sched_ext/state
cat /sys/kernel/sched_ext/root/ops
```

`state` が `enabled`、`ops` が `oreore` で始まることを確認する。
本文の出力例にある `aarch64` は、Windows の x86_64 VM では `x86_64` になる。
端末1で `Ctrl+C` を押し、端末2で `state` が `disabled` に戻ることを確認する。
戻らない場合は、端末2で `./scripts/guest/reset.sh` を実行する。

この後は[最初のスケジューラを動かす](./global.md)の説明と実験を、対応表に従って進める。
本文の「Mac 側で編集する」「Mac 側でコマンドを実行する」は、この手順では「端末1の VM 内で行う」と読み替える。
本文の `make vm-shell` は、PowerShell からの `multipass shell sched-ext-lab-win` に相当する。
本文で確認を終えて Mac 側へ戻す場面でも、Windows 版では VM に接続したままでよい。
`exit` した場合は、再接続して `cd ~/sched-ext-tutorial` を実行する。

## ソースを編集する

scheduler を終了してから、端末1で編集する。

```bash
nano lab/src/bpf/main.bpf.c
```

保存は `Ctrl+O`、Enter、終了は `Ctrl+X` で行う。
本文の `git diff` や `diff` も同じ VM 内で実行する。
ビルド対象は VM 内のファイルなので、Windows 側に別途取得したコピーを編集しても反映されない。

## 測定ログを残す

本文のパイプや `tee` は、VM 内の Bash でそのまま使える。
各実験の前に scheduler が `disabled` に戻っていることを確認する。

```bash
mkdir -p target/measurements
set -o pipefail
./scripts/guest/bench.sh fair 01 2>&1 | tee target/measurements/fair.log
```

長いスライスと短いスライスの実験は、それぞれ本文に従って `lab` を編集した後に行う。

```bash
./scripts/guest/bench.sh step lab 2>&1 | tee target/measurements/long.log
```

```bash
./scripts/guest/bench.sh step lab 2>&1 | tee target/measurements/short.log
```

CPU、バックエンド、ホスト負荷の違いが測定に混ざるため、Mac の数値との一致ではなく、同じ VM で方針を変えたときの差を比較する。
再現条件も VM 内で記録する。

```bash
cat /etc/sched-ext-tutorial/versions | tee target/measurements/versions.txt
uname -m | tee target/measurements/architecture.txt
git rev-parse HEAD | tee target/measurements/revision.txt
git diff -- lab/src/bpf/main.bpf.c > target/measurements/lab.diff
```

Windows 側へログを取り出す場合は、新しい **PowerShell** をログの保存先フォルダーで開き、次を実行する。

```powershell
New-Item -ItemType Directory -Force measurements | Out-Null
$logNames = 'fair.log', 'long.log', 'short.log', 'versions.txt', 'architecture.txt', 'revision.txt', 'lab.diff'
foreach ($logName in $logNames) {
    multipass transfer "sched-ext-lab-win:/home/ubuntu/sched-ext-tutorial/target/measurements/$logName" - |
        Set-Content -Encoding utf8 (Join-Path measurements $logName)
    if ($LASTEXITCODE -ne 0) { throw "ログの取得に失敗: $logName" }
}
multipass version | Out-File -Encoding utf8 multipass-version.txt
multipass get local.driver | Out-File -Encoding utf8 multipass-driver.txt
```

この方法はテキストログ用であり、バイナリファイルの転送には使わない。
検証環境では `multipass transfer --recursive` が Windows 側の権限設定でエラーを報告したため、テキストを読み出して保存する方法を使った。

## Windows での検証結果

2026年9月7日、Windows 11 Education（ビルド26200）、Ryzen 7 3800X、ホストメモリ32 GiB、Multipass 1.16.3 / Hyper-V で検証した。
ゲストは Ubuntu 26.04 amd64、Linux `7.0.0-30-generic`、4 vCPU、メモリ4 GiBである。
ソースは `3880ef03c5f1d8f89bd7930afbb6d8dabeaa4b3d` に、この章と x86_64 を受け入れる doctor の修正を加えたものを使った。

| 条件 | 平均遅延 | 最大遅延 | 期限超過 | context-switches |
|---|---:|---:|---:|---:|
| fair | 0.553 ms | 5.189 ms | 0 / 15 | 5,199 |
| STEP=03（2秒スライス） | 1,926.885 ms | 3,529.661 ms | 15 / 15 | 230 |
| STEP=04（10 msスライス） | 16.801 ms | 21.353 ms | 0 / 15 | 1,610 |

各条件1回、15標本の実測値であり、別のPCや再実行時に同じ数値になることは要求しない。
長いスライスから短いスライスへ変えると、遅延が減り、context-switches が増えることを確認できた。
生ログは [fair](../measurements/2026-09-07-windows/fair.txt)、[長いスライス](../measurements/2026-09-07-windows/long.txt)、[短いスライス](../measurements/2026-09-07-windows/short.txt)に保存した。

`make check`、全 checkpoint と `lab` のビルド、STEP=01〜04と `lab` の partial mode でのロードと SIGINT による解除、STEP=04 の system-wide mode、手動の SysRq 復旧が通った。
PowerShell の端末から `run-step.sh 01 partial` を起動し、実際の Ctrl+C で終了できることも確認した。
STEP=05 の system-wide mode では、次の停止理由と `disabled` を確認した。
この watchdog 検査中には手動の reset を実行していない。

```text
Error: EXIT: runnable task stall (watchdog failed to check in for 3.001s)
watchdog_exit=1 state=disabled
```

[起動・解除・復旧のログ](../measurements/2026-09-07-windows/runtime.txt)と[実際のツールの版](../measurements/2026-09-07-windows/versions.txt)も併せて参照できる。

## 終了と復旧

実験が終わったら scheduler を終了し、`state` が `disabled` に戻ったことを確認する。
VM 内の `exit` は接続を終了するだけで、VM は停止しない。
**PowerShell** から VM を停止する。

```powershell
multipass stop sched-ext-lab-win
```

端末1が応答しなくなったときは、別の **PowerShell** から教材の復旧スクリプトを呼ぶこともできる。

```powershell
multipass exec sched-ext-lab-win --working-directory /home/ubuntu/sched-ext-tutorial -- ./scripts/guest/reset.sh
```

手動で復旧した場合は、watchdog による自動復帰を確認した記録と分ける。

## つまずきやすい点

`multipass` が見つからない場合は、インストール後に PowerShell を開き直す。
VM が起動しない場合は、Hyper-V、CPU の仮想化機能、VM 用の空きメモリを確認し、[Multipass の起動トラブル対処](https://canonical.com/multipass/docs/latest/how-to-guides/troubleshoot/troubleshoot-launch-start-issues/)を参照する。

`/sys/kernel/sched_ext/state` がない、または `CONFIG_SCHED_CLASS_EXT` が無効な場合は、接続先とカーネルを `uname -r` で確認する。
WSL の Ubuntu と Multipass の Ubuntu は異なる環境である。
WSL では Ubuntu のユーザー空間を導入しても、実行中のカーネルが Ubuntu VM と同じになるわけではない。
この手順では、PowerShell から `multipass shell sched-ext-lab-win` で接続した実験 VM を使う。
WSL へ直接この教材を移す場合は、カーネル設定、perf、watchdog を含めた別の検証が必要である。

その他のビルド、ロード、測定の問題は[トラブルシューティング](../appendix/troubleshooting.md)を参照し、`make` コマンドはこの章の表で読み替える。
