# 高齢者向け安否確認システム - 実装手順書（改訂版）

## 1. 目的と全体像
- 実運用に耐える統合フロー（起動 → リアルタイム会話 → 感情分析・DB記録 → Google シート要約 → Gmail 通知）を確実に完結させる。
- 既存のリアルタイム会話品質を維持しつつ、アーキテクチャとファイル構成をプロダクション品質へ再構築する。
- 将来のスケジューラー連携やラズパイ運用を見据えた拡張性・保守性を確保する。

## 2. 新アーキテクチャ概要
```
project_root/
├── app/
│   ├── main.py                # エントリーポイント（DI & フロー起動）
│   ├── cli.py                 # CLI／引数ルーティング
│   └── runtime.py             # 起動〜終了の高レベル制御
├── core/
│   ├── conversation/
│   │   ├── session.py         # 会話セッション状態・フロー制御
│   │   └── pipeline.py        # 会話開始/終了と後処理のシナリオ管理
│   ├── analysis/
│   │   ├── emotion_service.py # 感情分析＋DB記録の統合
│   │   └── models.py          # ConversationResult 等の共通 DTO
│   └── notifications/
│       └── notifier_service.py# 通知判定と実行のオーケストレーション
├── infrastructure/
│   ├── audio/
│   │   └── realtime_handler.py# 既存 RealtimeAudioHandler を移設（内部ロジックは維持）
│   ├── db/
│   │   └── sqlite_repository.py# SQLite アクセス層（安全なマイグレーション）
│   ├── google/
│   │   ├── sheets_client.py   # gspread ラッパー
│   │   └── gmail_client.py    # Gmail API ラッパー
│   └── logging/
│       └── logger.py          # ログ設定
├── shared/
│   ├── config.py              # .env & 資格情報ローダー
│   ├── exceptions.py          # 共通例外
│   └── utils.py               # 汎用ユーティリティ
├── tests/
│   ├── core/...
│   └── e2e/...
└── credentials/, data/, docs/, requirements.txt など
```
- `infrastructure/audio/realtime_handler.py` には現行 `modules/audio_handler.py` を移設し、インタフェース層からの利用方法のみ調整する。
- 会話結果モデルは `core/analysis/models.py` に統合し、Google Sheets や通知が同一データを参照できるようにする。

## 3. 段階的移行ロードマップ
### Stage 0: 基盤整備とバックアップ
- 現行リポジトリをブランチ切り分け（例: `feature/system-refactor`）。
- `modules/audio_handler.py` の回帰テストを確認し、既存の会話品質が維持されていることを記録。
- `.env` と `credentials/` のバックアップと差異整理。

### Stage 1: ディレクトリと設定層の再構築
- `shared/config.py` を新設し、`.env` とサービスアカウント JSON ロードを一元管理。
- `modules/logger.py` を `infrastructure/logging/logger.py` に移し、全ファイルで import を更新。
- 既存 `main.py` を `app/main.py` へ移動し、最低限の DI ラッパに簡素化（ロジックは後続ステージで整理）。

### Stage 2: 会話コアの分離とフロー整備
- `core/conversation/session.py` を実装し、リアルタイム会話ハンドラのセッション管理・コールバック束ねを移行。
- `core/conversation/pipeline.py` を作成して、起動挨拶・リアルタイム会話開始・終了判定・後処理呼び出しをまとめる。
- `app/runtime.py` で `pipeline` を呼び出すだけの構造へ変換。リアルタイム会話ロジックには手を入れず、インタフェースのみ整える。

### Stage 3: 感情分析と DB 永続化の再設計
- `core/analysis/models.py` に `ConversationResult`, `EmotionAnalysis` 等を定義し、会話・分析・通知で共有。
- `EmotionRecordManager` を `core/analysis/emotion_service.py` に作り直し、`infrastructure/db/sqlite_repository.py` を経由して安全に保存（DROP TABLE を廃止）。
- 既存 DB をマイグレーションする場合は schema バージョン管理（例: `Alembic` またはカスタムマイグレーション）を導入。

### Stage 4: 外部連携の刷新
- `infrastructure/google/sheets_client.py` で gspread の遅延初期化とワークシート生成処理を整備。
- Gmail API ( `google-api-python-client` ) による通知送信を `infrastructure/google/gmail_client.py` に実装し、家族通知ロジックを `core/notifications/notifier_service.py` に集約。
- Google Sheets への書き込みやメール通知条件を `pipeline` の後処理に組み込む。

### Stage 5: 統合テストと運用準備
- `tests/core/` にユニットテスト（感情分析、通知判定など）、`tests/e2e/` に擬似会話フローの統合テストを追加。
- `.github/workflows/` 等で CI 設定（必要なら）。
- README / ドキュメント更新、ラズパイ deploy 手順整理。

## 4. 検証と品質確保
- **会話回帰テスト**: Stage 2 完了後に必ず実機でリアルタイム会話をテストし、挙動が変わらないことを確認。
- **DB 永続化テスト**: Stage 3 で既存データが保持されること、再起動で過去会話が残ることを確認。
- **Google Sheets / Gmail**: Stage 4 で sandbox 環境（別スプレッドシート・ダミーアカウント）を使い、権限・通信を検証。
- **エラーハンドリング**: ネットワーク遮断・API 失敗時の例外が適切に処理され、ログに記録されるか確認。

## 5. 依存関係と環境設定
- `requirements.txt` に以下を追加・整理：
  - `google-api-python-client`, `google-auth-httplib2`, `google-auth-oauthlib`（Gmail API）
  - `gspread`, `google-auth`（Google Sheets）
  - 既存: `openai`, `pyaudio`, `websockets`, `python-dotenv`, `tqdm` 等
- `.env` に必要なキー：
  - `OPENAI_API_KEY`
  - `OPENAI_REALTIME_MODEL`（例: `gpt-4o-realtime-preview-2024-10-01`）
  - `GOOGLE_SPREADSHEET_ID`
  - `GOOGLE_APPLICATION_CREDENTIALS`（サービスアカウント JSON パス）
  - `GMAIL_USER`, `GMAIL_CLIENT_SECRET_PATH`, `GMAIL_TOKEN_PATH` 等

## 6. ドキュメント更新タスク一覧
1. README に新しい実行方法／フォルダ構成を反映。
2. 本手順書に沿って進捗を記録し、ステージごとにチェックリストを更新。
3. Google Sheets / Gmail 設定手順を `docs/google_sheets_setup.md` へ追記、Gmail API 版の手順書を新設。