# 高齢者向け安否確認システム

1日1回のAI会話による高齢者の安否確認システムです。

## 概要

- 時報音で会話開始
- 会話・脳トレ・日記記録
- 感情分析による安否確認
- 異常時の家族通知

## セットアップ

### 1. 必要な環境
- Python 3.11+
- OpenAI API キー

### 2. インストール手順

```bash
# リポジトリのクローンまたはダウンロード
cd rzpy2025_10

# 仮想環境作成
python3 -m venv elderly_safety_env
source elderly_safety_env/bin/activate  # macOS/Linux
# elderly_safety_env\Scripts\activate  # Windows

# 依存関係インストール
pip install --upgrade pip
pip install -r requirements.txt
```

### 3. 設定

```bash
# 環境変数ファイル作成
cp .env.example .env

# .envファイルを編集してAPIキーを設定
OPENAI_API_KEY=your_api_key_here
```

## 使用方法

### 基本的な実行

```bash
# プログラム実行
python main.py
```

### 終了方法

音声コマンドで終了：
- 「終わり」
- 「おしまい」
- 「さようなら」

または `Ctrl+C` で強制終了

**注意**: 終了後は再度 `python main.py` の実行が必要です。

## ファイル構成

```
rzpy2025_10/
├── main.py                     # メインプログラム
├── modules/                    # モジュール
│   ├── daily_conversation.py   # 1日1回会話
│   ├── emotion_analysis.py     # 感情分析
│   └── data_manager.py         # データ保存・通知
├── data/                       # 会話記録
├── docs/                       # ドキュメント
│   ├── system_specification.md # システム仕様
│   ├── implementation_guide.md # 実装手順
│   └── prompt_design.md        # 会話設計
├── requirements.txt            # 依存関係
├── .env                        # 設定ファイル
└── README.md                   # このファイル
```

## ドキュメント

- [システム仕様](docs/system_specification.md) - システム全体の機能・要件
- [実装手順](docs/implementation_guide.md) - 開発フェーズ・実装計画
- [会話設計](docs/prompt_design.md) - プロンプト・会話スタイル

## 開発環境

### 開発用（macOS）
- 基本テスト・開発用

### 本格運用（Raspberry Pi 5）
- 自動起動設定
- 定時実行機能

## トラブルシューティング

### よくある問題

1. **音声が聞こえない**
   - マイク・スピーカーの接続確認
   - 音量設定の確認

2. **API接続エラー**
   - インターネット接続確認
   - APIキーの設定確認

3. **プログラムが終了しない**
   - `Ctrl+C` で強制終了
   - 音声終了コマンドを明確に発音