# 高齢者向け安否確認システム

OpenAI Realtime APIを活用したリアルタイム音声会話による高齢者の安否確認システムです。

## 概要

このシステムは、高齢者の方と自然な音声会話を通じて日々の健康状態や心理状態を把握し、家族への通知機能を統合した見守り支援ツールです。

### 実装済み機能

**✅ Phase1: リアルタイム音声会話システム（完了）**
- OpenAI Realtime API による高品質な音声会話
- 時間帯別の自然な挨拶機能
- 高齢者向けに最適化された対話プロンプト
- 音声コマンドによる終了機能
- ✨ 相槌・フィラー自動無視機能（「うーん」「えっと」を無視）
- ✨ AI応答の自動キャンセル機能（繰り返し防止）

**✅ Phase2: 感情分析・データ記録（完了）**
- キーワード辞書ベースの感情分析システム
- SQLiteによる会話内容の永続化
- 感情スコア・安否ステータスの自動判定
- 健康トレンド分析機能

**✅ Phase3: 外部連携・通知（完了）**
- Google Sheets連携（家族との会話記録共有）
- Gmail API による異常時の自動メール通知
- 安否ステータスに応じた色分け表示

**📋 Phase4: 定時自動実行（部分実装）**
- スケジューラーモジュール実装済み
- main.pyへの統合は未完了
- Raspberry Pi自動起動設定は未実装

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
# macOS/Linux
# venv\Scripts\activate  # Windows

# 依存関係インストール
pip install --upgrade pip
pip install -r requirements.txt
```

### 3. 環境変数の設定

`.env` ファイルをプロジェクトルートに作成し、以下を設定してください：

```bash
# 必須設定
OPENAI_API_KEY=your_openai_api_key_here

# ユーザー情報
CARE_USER_NAME=利用者の名前

# Google Sheets連携（オプション）
GOOGLE_SPREADSHEET_ID=your_spreadsheet_id
# credentials/google_service_account.json に認証ファイルを配置

# Gmail通知（オプション）
GMAIL_USER=your_email@gmail.com
FAMILY_EMAILS=family1@example.com,family2@example.com
# data/credentials.json に OAuth2クライアント認証情報を配置
```

**Google Sheets / Gmail 連携のセットアップ手順**:
1. Google Cloud Console でプロジェクトを作成
2. Google Sheets API / Gmail API を有効化
3. サービスアカウント（Sheets用）または OAuth2（Gmail用）の認証情報を取得
4. 認証ファイルを指定のディレクトリに配置

## 使用方法

### 基本的な実行

```bash
# メインプログラム（統合版）
# リアルタイム会話 + 感情分析 + Google Sheets記録 + メール通知
python main.py

# シンプル版（開発・テスト用）
python simple_voice_chat.py

# リアルタイム音声会話のみ（開発用）
python realtime_voice_chat.py
```

**実行すると**:
1. 時間帯に応じた挨拶から会話開始
2. 音声認識とAI応答がリアルタイムで動作
3. 会話終了後、自動的に以下を実行：
   - 感情分析
   - データベースへの記録
   - Google Sheetsへの追加（設定済みの場合）
   - 異常検知時のメール通知（設定済みの場合）

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
├── main.py                         # メインプログラム（統合版）
├── simple_voice_chat.py            # シンプル版（開発・テスト用）
├── realtime_voice_chat.py          # リアルタイム音声会話のみ（開発用）
├── test_google_sheets.py           # Google Sheets接続テスト
│
├── modules/                        # モジュール群
│   ├── audio_handler.py           # ✅ リアルタイム音声処理（Realtime API）
│   ├── emotion_analyzer.py        # ✅ 感情分析・DB記録（SQLite）
│   ├── safety_checker.py          # ✅ 安否確認システム
│   ├── google_sheets.py           # ✅ Google Sheets連携
│   ├── email_notifier.py          # ✅ Gmail通知システム
│   ├── scheduler.py               # ⚠️ スケジューラー（実装済み、統合未完了）
│   ├── config.py                  # ✅ 設定管理
│   ├── logger.py                  # ✅ ログ管理
│   ├── time_announcement.py       # 📋 時報機能（未使用）
│   └── daily_conversation.py      # 📋 日次会話管理（未使用）
│
├── data/                           # データディレクトリ
│   ├── conversations.db           # 会話記録データベース（自動生成）
│   ├── credentials.json           # Gmail OAuth2認証（手動配置）
│   └── token.json                 # Gmail認証トークン（自動生成）
│
├── credentials/                    # 認証情報ディレクトリ
│   └── google_service_account.json # Google Sheets認証（手動配置）
│
├── logs/                           # ログファイル
│   └── app.log                    # アプリケーションログ（自動生成）
│
├── docs/                           # ドキュメント
│   ├── system_specification.md    # システム仕様書
│   ├── implementation_guide.md    # 実装手順書（フェーズ別実装状況）
│   ├── prompt_design.md           # 会話プロンプト設計
│   ├── 会話品質調整ガイド.md      # ✨ Realtime APIパラメータ調整ガイド
│   └── 未実装機能リスト.md         # 初期仕様との差分リスト
│
├── agents/                         # AI開発支援プロンプト集
├── prompts/                        # 開発用プロンプトテンプレート
│
├── requirements.txt                # Python依存パッケージ
├── .env                            # 環境変数設定（手動作成）
├── .gitignore                      # Git除外設定
└── README.md                       # このファイル
```

**凡例**:
- ✅ 完全実装済み・使用中
- ⚠️ 実装済みだが統合未完了
- 📋 実装済みだが未使用/開発中
- ✨ 最近追加された重要ドキュメント

## ドキュメント

### 📚 仕様・設計ドキュメント
- [システム仕様書](docs/system_specification.md) - システム全体の機能・要件定義
- [実装手順書](docs/implementation_guide.md) - 開発フェーズ・実装状況・完成度
- [プロンプト設計書](docs/prompt_design.md) - 高齢者向け会話プロンプト設計
- [未実装機能リスト](docs/未実装機能リスト.md) - 初期仕様との差分・今後の課題

### 🛠️ 開発・調整ガイド
- [会話品質調整ガイド](docs/会話品質調整ガイド.md) - ⭐ **重要** Realtime APIパラメータの詳細解説
  - 全パラメータのリファレンス
  - 数値による動作の変化
  - 相槌・フィラー無視機能
  - AI応答自動キャンセル機能
  - トラブルシューティング

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