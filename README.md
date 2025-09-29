# 高齢者向け安否確認システム

1日1回のAI会話による高齢者の安否確認システムです。

## 概要

**Phase1完成済み**: 
- ✅ **時報音で会話開始** - 時間帯別挨拶機能
- ✅ **AI会話システム** - Whisper + GPT-4o + TTS統合
- ✅ **高齢者向けプロンプト** - 仕様書準拠の対話スタイル
- ✅ **音声終了コマンド** - 自然な終了操作

**Phase2完了**:
- ✅ 感情分析による安否確認（キーワード辞書ベース）
- ✅ 会話内容のデータベース保存（SQLite）
- ✅ 健康要約・トレンド取得API
- 📋 ダッシュボード可視化（次フェーズ）

**Phase3以降の予定**:
- 📋 異常時の家族通知

## セットアップ

### 1. 必要な環境
- Python 3.11+
- OpenAI API キー

### 2. インストール手順

```bash
# リポジトリのクローンまたはダウンロード
cd rzpy2025_10

# 仮想環境作成
python3 -m venv venv
source venv/bin/activate  # macOS/Linux
# venv\Scripts\activate  # Windows

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
# メインプログラム（完全版）
python main.py

# シンプル版（テスト用）
python simple_voice_chat.py

# Realtime API を使ったテキスト会話（今回追加）
python realtime_companion.py

# Realtime API を使った音声会話（今回追加）
python realtime_voice_chat.py

# websockets が古い場合のアップグレード
pip install --upgrade websockets

# OPENAI_MODEL を .env に設定していない場合のテスト用モデル
# （実運用では OpenAI の最新サポートモデルを指定してください）
export OPENAI_MODEL="gpt-4o-realtime-preview-2024-10-01"
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
├── main.py                     # メインプログラム（完全版）
├── simple_voice_chat.py        # シンプル版（テスト用）
├── realtime_companion.py       # Realtime API を使った共感型テキスト会話
├── modules/                    # モジュール
│   ├── config.py              # 設定管理（実装済み）
│   ├── logger.py              # ログ管理（実装済み）
│   ├── __init__.py            # パッケージ初期化（実装済み）
│   ├── daily_conversation.py  # Phase2用（未実装）
│   ├── emotion_analyzer.py    # Phase2用（実装済み）
│   ├── safety_checker.py      # Phase3用（未実装）
│   └── scheduler.py           # Phase4用（未実装）
├── data/                       # 会話記録
├── logs/                       # ログファイル
├── docs/                       # ドキュメント
│   ├── system_specification.md # システム仕様
│   ├── implementation_guide.md # 実装手順
│   └── prompt_design.md        # 会話設計
├── requirements.txt            # 依存関係（整理済み）
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