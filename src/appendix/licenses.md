# ライセンスと由来

本文は Creative Commons Attribution 4.0 International（CC BY 4.0）で提供する。
独自に作成した負荷生成器、VM 操作スクリプト、検査スクリプトは MIT OR Apache-2.0で提供する。

教材の BPF scheduler は、Linux 6.18 の `tools/sched_ext/scx_simple.bpf.c` を基にしている。
元コードと派生した scheduler、Rust ローダーは GPL-2.0-only とする。
なお、6.18 はコードの由来である。
教材が動作確認を行った実行対象のカーネルは、[固定したバージョン](./versions.md)に記載のとおりであり、由来と実行対象は別の役割を持つ。

各ファイルの SPDX identifier と package manifest の `license` フィールドを、そのファイルに適用するライセンスの基準とする。
ライセンスの全文は [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/legalcode)、[MIT](https://opensource.org/license/mit)、[Apache License 2.0](https://www.apache.org/licenses/LICENSE-2.0)、[GPL-2.0-only](https://www.gnu.org/licenses/old-licenses/gpl-2.0.html) から確認できる。

主な参照元は次のとおりである。

- [Linux 6.18 sched_ext documentation](https://docs.kernel.org/6.18/scheduler/sched-ext.html)
- [Linux v6.18 scx_simple.bpf.c](https://github.com/gregkh/linux/blob/v6.18/tools/sched_ext/scx_simple.bpf.c)
- [sched-ext/scx v1.1.3](https://github.com/sched-ext/scx/tree/v1.1.3)
- [scxtop v1.1.3](https://github.com/sched-ext/scx/tree/v1.1.3/tools/scxtop)
