# 実機で評価する

VM は callback と DSQ の動作を学ぶ環境として使える。
しかし、VM 上の4 vCPUは物理 CPU コアそのものではなく、ホスト scheduler が割り当てる実行単位である。

LLC、NUMA、SMT、CPU 周波数、電力、対話応答性を評価する場合は、再起動可能な Linux 実機を使う。
その場合も、次の条件を記録する。

- CPU とメモリの構成
- kernel、firmware、`scx` の版
- CPU governor と SMT の状態
- バックグラウンドサービス
- workload の CPU affinity
- warm-up、試行時間、反復回数

VM で得た絶対値を実機の予測値として使わない。
VM の結果が示したのは、固定した環境内で方針を変えると観測値も変わるという因果関係である。

