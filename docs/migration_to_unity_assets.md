# プロジェクト移行手順書: PythonプロジェクトをUnity内に統合する

現在の制約（AgentがUnityプロジェクト外のファイルを編集できない）を解決し、**Unity主導アーキテクチャ** を円滑に進めるため、Pythonプロジェクト (`ghostless`) を Unityプロジェクト (`simulacra-2`) の中に移動させます。

## 目標
*   **Unityプロジェクト**: `/Users/mh/simulacra-2`
*   **配置先**: `/Users/mh/simulacra-2/Assets/Ghostless` (新規フォルダ)
*   これにより、Agentは C# スクリプトと Python スクリプトの両方を自由に編集できるようになります。

---

## 手順 1: Unityプロジェクト内にフォルダを作成

ターミナルで以下のコマンドを実行し、UnityのAssetsフォルダ内に移動先を作成します。

```bash
mkdir -p /Users/mh/simulacra-2/Assets/Ghostless
```

## 手順 2: 現在のリポジトリを移動（またはClone）

**方法 A: 現在の作業フォルダをそのまま移動する場合（推奨）**
これまでの作業履歴（Gitログなど）を保持したまま移動します。

```bash
# 現在のディレクトリから移動
mv /Users/mh/dev/ghostless/* /Users/mh/simulacra-2/Assets/Ghostless/
mv /Users/mh/dev/ghostless/.gitignore /Users/mh/simulacra-2/Assets/Ghostless/
mv /Users/mh/dev/ghostless/.git /Users/mh/simulacra-2/Assets/Ghostless/
```

**方法 B: 新しくCloneし直す場合**
もし今の環境を残したい場合は、RepoをCloneします。（URLは仮定です。ローカルGitの場合はコピーでOK）

```bash
cp -R /Users/mh/dev/ghostless/ /Users/mh/simulacra-2/Assets/Ghostless/
```

## 手順 3: 不要なファイルの整理

UnityのAssetsフォルダ内にPython仮想環境 (`.venv`) や キャッシュ (`__pycache__`) があると、Unityがインポートしようとして重くなる（またはエラーが出る）可能性があります。

1.  **Unityが無視するように設定**
    移動したフォルダ (`Assets/Ghostless`) 内の `.venv` などのフォルダ名の末尾に `~` をつけるか、隠しフォルダにするとUnityは無視しますが、最も確実なのは **「Python専用フォルダ」を作り、Unityメタデータを作成させない** ことです。
    
    *   しかし、スクリプト (`.py`) はTextAssetとして認識されても問題ありません。
    *   **重要**: `.venv` フォルダは削除し、新しい場所で作り直すことを強く推奨します。

```bash
# 旧.venvの削除
rm -rf /Users/mh/simulacra-2/Assets/Ghostless/.venv

# Pythonの一時ファイル削除
find /Users/mh/simulacra-2/Assets/Ghostless -name "__pycache__" -type d -exec rm -rf {} +
```

## 手順 4: 新しい環境でのセットアップ

新しい場所でPython環境を再構築します。

```bash
cd /Users/mh/simulacra-2/Assets/Ghostless

# 仮想環境の作成
python3 -m venv .venv
source .venv/bin/activate

# 依存関係のインストール
pip install -r prototype/requirements.txt
```

## 手順 5: Agentへのワークスペース追加

これが最も重要なステップです。
Agentに対して、新しい作業場所 **`/Users/mh/simulacra-2`** をワークスペースとして認識させる必要があります。

1.  このチャットセッションを終了（またはリセット）します。
2.  新しいチャットを開始する際、**作業ディレクトリとして `/Users/mh/simulacra-2` を指定** して開いてください。

これで、Agentは `Assets/GhostlessReceiver.cs` も `Assets/Ghostless/scripts/simulacra_v2.py` も両方編集できるようになります。
