# 3tene PRO 外部制御連携の調査と実装まとめ

本ドキュメントは、3tene PROのアバターを外部Pythonスクリプトから制御し、「シミュラクラ（自律的な振る舞い）」を実装するための技術調査と試行錯誤の全記録です。

## 1. 目的
- 3tene PROのアバターに対して、**呼吸（Breathing）** や **視線（Gaze）** などの微細な動きをプログラムで送り込み、生きているような質感を出すこと。
- GUI操作や既存のモーション再生ではなく、リアルタイムな外部制御を確立すること。

## 2. 試行錯誤の経緯

### フェーズ1: VMC Protocol (OSC) の模索
- **仮説**: 多くのVTuberソフトが対応している「VMC Protocol (OSC)」が3teneでも使えるはず。
- **検証**:
    - ポート `39539` (VMC標準) への送信テスト。
    - 結果: **反応なし**。
- **結論**: **3tene PRO V4はVMC Protocolの受信に非対応** であることが判明（公式ドキュメントおよびユーザー調査による）。

### フェーズ2: Mocopi (UDP 12351) の偽装
- **方針**: 3teneが公式対応している「Sony Mocopi」のふりをしてデータを送る。
- **構成**: `Python Spoofer` -> (UDP 12351) -> `3teneMoApp_Mocopi` -> `3tene PRO`
- **実装**:
    - `mocopi-parser` (Rust製OSS) を参考にバイナリプロトコルを完全再現。
    - `Head`, `Info` (sndf), `Fram` 構造体を作成。
    - 公式互換受信機 (`mcp-receiver`) では正常にパケットとして認識されることを確認。
    - **結果**: **3teneMoApp上でアバターが動かない**。
- **分析**: `3teneMoApp` アプリ側で、データの正当性以外にも「キャリブレーションシーケンス」や「特定センサー値のチェック」などのブラックボックスな検証が行われており、単純なパケット再生では突破できないと判断。

### フェーズ3: 内部通信 (TCP 3910) の解析とハック【成功】
- **発見**: `3tene PRO` と `3teneMoApp` を同時起動すると、ローカルホストの **TCP 3910** ポートで接続していることを `lsof` コマンドで特定。
- **推測**: ポート3910は通常「Leap Motion」で使用される。`3teneMoApp` はLeap Motionのふり、あるいはLeap Motion用の通信経路を借用してデータを送っているのではないか。
- **解析**:
    - `tcpdump` を用いて、実際のアプリ間通信をキャプチャ。
    - **プロトコル判明**: Line-delimited JSON (1行ごとのJSON)。
- **実装**:
    - PythonでTCPサーバーを立ち上げ、3teneからの接続を待つスクリプトを作成。
    - 解析したJSONを送出したところ、**アバターの制御に成功**。

## 3. 技術仕様 (TCP 3910 Protocol)

Pythonから送信するJSONフォーマットの仕様です。

**接続方式:**
- Python側: TCP Server (Bind 3910)
- 3tene側: TCP Client (Connect localhost:3910)
- `3teneMoApp` は**終了しておく必要がある**（ポート競合するため）。

**データ形式:**
```json
{
  "Version": 2,
  "DeviceID": 9,
  "DeviceType": 2,
  "Slot": 0,
  "Position": { "x": 0.0, "y": 0.0, "z": 0.0 },
  "Bones": [
    { "type": 0, "qt_x": 0.0, "qt_y": 0.0, "qt_z": 0.0, "qt_w": 1.0 },
    ...
  ],
  "Command": { "Number": -1 }
}
```

**ボーンIDマッピング (検証済み):**
- **0**: Hips (Root) - 重心移動、呼吸の上下
- **1, 2**: Spine/Chest (推定) - 呼吸の胸の動き
- **9, 10**: **Head/Neck** - 視線、うなずき
- **14, 15**: Arms (推定)

## 4. 今後の展望
このTCP制御スクリプト (`tcp_3tene_spoofer.py` 改め `simulacra_core.py`) をベースに、自律動作ロジックを実装します。

以上
