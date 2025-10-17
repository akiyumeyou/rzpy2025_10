# 高齢者向け安否確認システム - 実装手順書

## 1. プロジェクト概要

### 1.1 システム構成
このシステムは、OpenAI Realtime APIを中心としたリアルタイム音声会話システムに、感情分析、データ記録、外部連携（Google Sheets / Gmail）を統合した高齢者見守り支援システムです。

### 1.2 技術スタック
- **プログラミング言語**: Python 3.11+
- **音声処理**: OpenAI Realtime API (WebSocket)
- **音声I/O**: PyAudio
- **データベース**: SQLite3
- **外部API**: Google Sheets API, Gmail API
- **認証**: Google OAuth2, Service Account

---

## 2. 実装フェーズと完了状況

### Phase 1: リアルタイム音声会話システム ✅ **完了**

**目標**: OpenAI Realtime APIを使った高品質な音声会話の実現

**実装内容**:
- ✅ `audio_handler.py`: リアルタイム音声処理クラス
  - WebSocket接続管理
  - 音声入力のストリーミング送信
  - 音声出力の受信・再生
  - Server VAD（音声検知）の活用
- ✅ `main.py`: メインアプリケーション
  - 時間帯別挨拶機能
  - 終了コマンド検知
  - 会話フロー管理
- ✅ `prompt_design.md`: 高齢者向けプロンプト設計
  - 共感的な対話スタイル
  - 短く簡潔な応答
  - 脳トレ・記憶ゲーム提案

**成果物**:
- リアルタイムで自然な音声会話が可能
- 遅延が少なく、音声認識精度が高い
- 終了コマンドで適切に会話終了

---

### Phase 2: 感情分析・データ記録 ✅ **完了**

**目標**: 会話内容の分析と永続化

**実装内容**:
- ✅ `emotion_analyzer.py`: 感情分析システム
  - キーワード辞書ベースの感情分析
  - 6つの感情カテゴリ分類（positive, negative, anxious, depressed, energetic, neutral）
  - 健康指標の抽出（痛み、疲労、睡眠、食欲、服薬など）
  - 信頼度スコアの算出
- ✅ `emotion_analyzer.py`: データベース管理
  - SQLiteでの会話記録保存
  - 感情分析結果の記録
  - 最近の会話取得API
  - 感情トレンド分析API
- ✅ `safety_checker.py`: 安否確認ロジック
  - SafetyStatus判定（safe, needs_attention, emergency, unknown）
  - 緊急キーワード検知
  - フォローアップ必要性判定

**成果物**:
- 会話ごとの感情分析レポート
- データベースに蓄積された会話履歴
- 時系列での感情トレンド分析が可能

---

### Phase 3: 外部連携・通知機能 ✅ **完了**

**目標**: 家族との情報共有と異常時の自動通知

**実装内容**:
- ✅ `google_sheets.py`: Google Sheets連携
  - gspread による Sheets API 利用
  - Service Account 認証
  - 会話記録の自動追加
  - 安否ステータスに応じた色分け
  - 最近の記録取得・サマリーレポート生成
- ✅ `email_notifier.py`: Gmail 通知システム
  - Gmail API + OAuth2 認証
  - 異常検知時の自動メール送信
  - 通知条件判定（emergency, needs_attention, 感情スコア低下）
  - 家族への詳細レポート送信

**成果物**:
- 会話記録がGoogle Sheetsにリアルタイム保存
- 異常時に家族へ自動メール通知
- 視覚的に分かりやすい記録管理

---

### Phase 4: 定時自動実行・スケジューラー ⚠️ **部分実装**

**目標**: 指定時刻に自動的に安否確認を実行

**実装内容**:
- ✅ `scheduler.py`: スケジューラーモジュール
  - schedule ライブラリによる定時実行
  - 複数時刻のスケジュール管理
  - スケジュールの有効化/無効化
  - 時報アナウンス機能
- ⚠️ `main.py`への統合: **未完了**
  - 現在は手動実行のみ
  - スケジューラーを main.py に統合する必要あり
- 📋 Raspberry Pi 自動起動: **未実装**
  - systemd サービス化
  - 起動時の自動実行設定

**今後の作業**:
1. `main.py` にスケジューラー統合
2. Raspberry Pi での動作テスト
3. systemd サービスファイル作成
4. 自動起動設定の文書化

---

### Phase 5: エラーハンドリング・耐障害性 📋 **未実装**

**目標**: ネットワーク障害やエラー発生時の適切な対応

**計画中の実装**:
- 📋 ネットワーク切断時の再接続処理
- 📋 音声認識失敗時のリトライ機構
- 📋 API呼び出しのタイムアウト管理
- 📋 オフライン時の基本機能継続
- 📋 エラーログの詳細記録と分析

---

### Phase 6: ダッシュボード・可視化 📋 **未実装**

**目標**: 家族向けのWebダッシュボード

**計画中の実装**:
- 📋 Flask/FastAPI による Web アプリケーション
- 📋 感情トレンドのグラフ表示
- 📋 安否確認履歴の一覧表示
- 📋 リアルタイム通知の表示
- 📋 設定変更UI

---

## 3. ファイル構成と役割

### 3.1 コアモジュール（実装済み）

| ファイル | 役割 | 状態 |
|---------|-----|------|
| `main.py` | メインアプリケーション | ✅ 完了 |
| `modules/audio_handler.py` | リアルタイム音声処理 | ✅ 完了 |
| `modules/emotion_analyzer.py` | 感情分析・DB管理 | ✅ 完了 |
| `modules/safety_checker.py` | 安否確認ロジック | ✅ 完了 |
| `modules/google_sheets.py` | Google Sheets連携 | ✅ 完了 |
| `modules/email_notifier.py` | Gmail通知 | ✅ 完了 |
| `modules/config.py` | 設定管理 | ✅ 完了 |
| `modules/logger.py` | ログ管理 | ✅ 完了 |

### 3.2 部分実装・未使用モジュール

| ファイル | 役割 | 状態 |
|---------|-----|------|
| `modules/scheduler.py` | 定時実行スケジューラー | ⚠️ 実装済み、統合未完了 |
| `modules/time_announcement.py` | 時報機能 | 📋 実装済み、未使用 |
| `modules/daily_conversation.py` | 日次会話管理 | 📋 実装済み、未使用 |

---

## 4. 設定と認証

### 4.1 必須環境変数（`.env`）

```bash
# OpenAI API
OPENAI_API_KEY=sk-...

# ユーザー情報
CARE_USER_NAME=利用者名
```

### 4.2 オプション環境変数

```bash
# Google Sheets連携
GOOGLE_SPREADSHEET_ID=spreadsheet_id

# Gmail通知
GMAIL_USER=your_email@gmail.com
FAMILY_EMAILS=family1@example.com,family2@example.com
```

### 4.3 認証ファイル

| ファイル | 用途 | 配置場所 |
|---------|-----|---------|
| `google_service_account.json` | Google Sheets認証 | `credentials/` |
| `credentials.json` | Gmail OAuth2 | `data/` |
| `token.json` | Gmail認証トークン | `data/` (自動生成) |

---

## 5. 開発・運用ガイド

### 5.1 開発環境でのテスト

```bash
# 仮想環境の有効化
source venv/bin/activate

# 依存パッケージのインストール
pip install -r requirements.txt

# メインプログラムの実行
python main.py
```

### 5.2 Google Sheets連携のテスト

```bash
# Google Sheets接続テスト
python modules/google_sheets.py
```

### 5.3 Gmail通知のテスト

```bash
# Gmail通知システムのテスト
python modules/email_notifier.py
```

### 5.4 本番環境（Raspberry Pi）へのデプロイ（計画中）

**手順**:
1. Raspberry Pi OS のセットアップ
2. Python 3.11+ のインストール
3. プロジェクトのクローン
4. 依存パッケージのインストール
5. 環境変数の設定
6. systemd サービス化
7. 自動起動の有効化

---

## 6. 今後の課題と改善点

### 6.1 機能面の課題

1. **定時自動実行の統合**
   - スケジューラーモジュールをmain.pyに統合
   - 複数ユーザー対応

2. **エラーハンドリングの強化**
   - ネットワーク障害への対応
   - API呼び出しのリトライ機構

3. **オフライン対応**
   - ネットワーク切断時の基本機能維持
   - ローカルでの会話記録保存

### 6.2 システム面の課題

1. **Raspberry Pi対応**
   - PyAudioの動作確認
   - 音声デバイス設定の最適化
   - systemdサービス化

2. **セキュリティ**
   - 認証情報の安全な管理
   - 通信の暗号化

3. **パフォーマンス**
   - 音声処理の最適化
   - データベースクエリの効率化

### 6.3 ユーザビリティ

1. **設定UIの提供**
   - Webベースの設定画面
   - スケジュール管理UI

2. **家族向けダッシュボード**
   - 会話履歴の可視化
   - 感情トレンドのグラフ表示

---

## 7. まとめ

### 7.1 現在の完成度

- **Phase 1（音声会話）**: ✅ 100% 完了
- **Phase 2（感情分析・記録）**: ✅ 100% 完了
- **Phase 3（外部連携・通知）**: ✅ 100% 完了
- **Phase 4（定時実行）**: ⚠️ 60% 完了（スケジューラー実装済み、統合未完了）
- **Phase 5（エラー処理）**: 📋 20% 完了（基本的なログのみ）
- **Phase 6（ダッシュボード）**: 📋 0% 未着手

**総合完成度**: 約 **70%**

### 7.2 実運用に向けて

現在のシステムは、手動実行による安否確認システムとしては**実用レベル**に達しています。

**すぐに使える機能**:
- リアルタイム音声会話
- 感情分析と安否判定
- Google Sheetsへの記録
- 異常時のメール通知

**実運用に必要な追加作業**:
- 定時自動実行の統合
- Raspberry Piでの動作確認
- systemdサービス化
- エラーハンドリングの強化

---

**最終更新**: 2025年9月30日