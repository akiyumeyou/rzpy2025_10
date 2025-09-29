"""
Googleシート連携モジュール
会話記録を家族と共有するためのGoogleシート操作
"""

import json
import os
import sys
from datetime import datetime
from typing import Optional, Dict, List, Any
from dataclasses import asdict

try:
    import gspread
    from google.auth.exceptions import DefaultCredentialsError
    from google.oauth2.service_account import Credentials
except ImportError:
    gspread = None
    DefaultCredentialsError = Exception
    Credentials = None

from .logger import get_logger
from .safety_checker import ConversationResult, SafetyStatus

logger = get_logger(__name__)

class GoogleSheetsManager:
    """Googleシート管理クラス"""

    def __init__(self):
        self.client = None
        self.spreadsheet = None
        self.worksheet = None
        self.credentials_path = os.path.join(os.path.dirname(__file__), '..', 'credentials', 'google_service_account.json')
        self.spreadsheet_id = os.getenv('GOOGLE_SPREADSHEET_ID', '')

        if not gspread:
            logger.warning("gspread モジュールがインストールされていません。Google Sheets機能を無効化します。")
            return

        self._initialize_client()

    def _initialize_client(self):
        """Google Sheetsクライアントの初期化"""
        try:
            if not os.path.exists(self.credentials_path):
                logger.warning(f"Google サービスアカウント認証ファイルが見つかりません: {self.credentials_path}")
                logger.info("Google Sheets連携を有効にするには、サービスアカウントのJSONファイルを配置してください")
                return

            # スコープの設定
            scopes = [
                'https://www.googleapis.com/auth/spreadsheets',
                'https://www.googleapis.com/auth/drive'
            ]

            # 認証情報の読み込み
            credentials = Credentials.from_service_account_file(
                self.credentials_path,
                scopes=scopes
            )

            # gspreadクライアントの初期化
            self.client = gspread.authorize(credentials)

            if self.spreadsheet_id:
                self._initialize_spreadsheet()
            else:
                logger.warning("GOOGLE_SPREADSHEET_ID が設定されていません")

        except FileNotFoundError:
            logger.error(f"認証ファイルが見つかりません: {self.credentials_path}")
        except DefaultCredentialsError as e:
            logger.error(f"Google認証エラー: {e}")
        except Exception as e:
            logger.error(f"Google Sheetsクライアント初期化エラー: {e}")

    def _initialize_spreadsheet(self):
        """スプレッドシートとワークシートの初期化"""
        try:
            # スプレッドシートを開く
            self.spreadsheet = self.client.open_by_key(self.spreadsheet_id)

            # '安否確認記録'ワークシートを取得または作成
            try:
                self.worksheet = self.spreadsheet.worksheet('安否確認記録')
            except gspread.exceptions.WorksheetNotFound:
                logger.info("'安否確認記録'ワークシートが見つかりません。新規作成します。")
                self.worksheet = self.spreadsheet.add_worksheet(
                    title='安否確認記録',
                    rows=1000,
                    cols=10
                )
                self._setup_header()

            logger.info(f"Google Sheets連携が初期化されました: {self.spreadsheet.title}")

        except gspread.exceptions.SpreadsheetNotFound:
            logger.error(f"スプレッドシートが見つかりません: {self.spreadsheet_id}")
        except Exception as e:
            logger.error(f"スプレッドシート初期化エラー: {e}")

    def _setup_header(self):
        """ワークシートのヘッダー行を設定"""
        if not self.worksheet:
            return

        headers = [
            '日時', 'ユーザー名', '会話時間(分)', '安否ステータス',
            '感情スコア', 'キーワード', '要約', 'フォローアップ必要',
            'ユーザー発言', 'AI応答'
        ]

        try:
            self.worksheet.update('A1:J1', [headers])

            # ヘッダー行のスタイル設定
            self.worksheet.format('A1:J1', {
                'backgroundColor': {'red': 0.8, 'green': 0.8, 'blue': 0.8},
                'textFormat': {'bold': True}
            })

            logger.info("ワークシートヘッダーを設定しました")

        except Exception as e:
            logger.error(f"ヘッダー設定エラー: {e}")

    def is_available(self) -> bool:
        """Google Sheets機能が利用可能かチェック"""
        return (gspread is not None and
                self.client is not None and
                self.worksheet is not None)

    def record_conversation(self, result: ConversationResult, user_name: str = "利用者") -> bool:
        """会話記録をGoogle Sheetsに保存"""
        if not self.is_available():
            logger.warning("Google Sheets機能が利用できません")
            return False

        try:
            # 日時の変換
            timestamp = datetime.fromisoformat(result.timestamp.replace('Z', '+00:00'))
            date_str = timestamp.strftime('%Y-%m-%d %H:%M:%S')

            # 会話時間（分）
            duration_min = round(result.duration / 60, 1)

            # キーワードの結合
            keywords_str = ', '.join(result.keywords) if result.keywords else ''

            # ユーザー発言の結合（最大500文字）
            user_text = ' | '.join(result.user_responses)
            if len(user_text) > 500:
                user_text = user_text[:497] + '...'

            # AI応答の結合（最大500文字）
            ai_text = ' | '.join(result.ai_responses)
            if len(ai_text) > 500:
                ai_text = ai_text[:497] + '...'

            # 行データの準備
            row_data = [
                date_str,
                user_name,
                duration_min,
                result.safety_status.value,
                round(result.emotion_score, 2),
                keywords_str,
                result.summary,
                'はい' if result.needs_followup else 'いいえ',
                user_text,
                ai_text
            ]

            # 次の空行を見つけて追加
            next_row = len(self.worksheet.get_all_values()) + 1
            self.worksheet.update(f'A{next_row}:J{next_row}', [row_data])

            # ステータスに応じたセルの色付け
            self._apply_status_formatting(next_row, result.safety_status)

            logger.info(f"Google Sheetsに会話記録を保存しました (行: {next_row})")
            return True

        except Exception as e:
            logger.error(f"Google Sheets記録エラー: {e}")
            return False

    def _apply_status_formatting(self, row: int, status: SafetyStatus):
        """ステータスに応じたセルの色付け"""
        try:
            if status == SafetyStatus.EMERGENCY:
                # 緊急時は赤色
                color = {'red': 1.0, 'green': 0.8, 'blue': 0.8}
            elif status == SafetyStatus.NEEDS_ATTENTION:
                # 要注意は黄色
                color = {'red': 1.0, 'green': 1.0, 'blue': 0.8}
            elif status == SafetyStatus.SAFE:
                # 安全は薄緑
                color = {'red': 0.8, 'green': 1.0, 'blue': 0.8}
            else:
                # 不明は薄グレー
                color = {'red': 0.9, 'green': 0.9, 'blue': 0.9}

            self.worksheet.format(f'A{row}:J{row}', {
                'backgroundColor': color
            })

        except Exception as e:
            logger.warning(f"セル色付けエラー: {e}")

    def get_recent_records(self, days: int = 7) -> List[Dict[str, Any]]:
        """最近の記録を取得"""
        if not self.is_available():
            return []

        try:
            # 全データを取得
            records = self.worksheet.get_all_records()

            if not records:
                return []

            # 日付でフィルタリング
            cutoff_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            cutoff_date = cutoff_date.replace(day=cutoff_date.day - days)

            recent_records = []
            for record in records:
                try:
                    record_date = datetime.strptime(record['日時'], '%Y-%m-%d %H:%M:%S')
                    if record_date >= cutoff_date:
                        recent_records.append(record)
                except (ValueError, KeyError):
                    continue

            logger.info(f"過去{days}日間の記録を{len(recent_records)}件取得しました")
            return recent_records

        except Exception as e:
            logger.error(f"記録取得エラー: {e}")
            return []

    def generate_summary_report(self, days: int = 7) -> Optional[str]:
        """サマリーレポートを生成"""
        records = self.get_recent_records(days)

        if not records:
            return f"過去{days}日間の記録がありません。"

        # 統計情報の計算
        total_conversations = len(records)
        safe_count = sum(1 for r in records if r.get('安否ステータス') == 'safe')
        attention_count = sum(1 for r in records if r.get('安否ステータス') == 'attention')
        emergency_count = sum(1 for r in records if r.get('安否ステータス') == 'emergency')

        # 平均感情スコア
        emotion_scores = []
        for r in records:
            try:
                score = float(r.get('感情スコア', 0))
                emotion_scores.append(score)
            except (ValueError, TypeError):
                continue

        avg_emotion = sum(emotion_scores) / len(emotion_scores) if emotion_scores else 0

        # レポート作成
        report = f"""
【過去{days}日間の安否確認サマリー】

📊 基本統計:
・会話回数: {total_conversations}回
・平均感情スコア: {avg_emotion:.2f}

🏥 安否状況:
・安全: {safe_count}回 ({safe_count/total_conversations*100:.1f}%)
・要注意: {attention_count}回 ({attention_count/total_conversations*100:.1f}%)
・緊急: {emergency_count}回 ({emergency_count/total_conversations*100:.1f}%)

⚠️ 注意事項:
"""

        if emergency_count > 0:
            report += f"・緊急状況が{emergency_count}回発生しています。すぐに確認してください。\n"
        elif attention_count > total_conversations * 0.3:
            report += "・要注意の記録が多く見られます。様子を確認することをお勧めします。\n"
        else:
            report += "・特に心配な状況は見られません。\n"

        return report

# 使用例とテスト用の関数
def test_google_sheets_connection():
    """Google Sheets接続テスト"""
    print("Google Sheets接続テストを開始...")

    manager = GoogleSheetsManager()

    if manager.is_available():
        print("✅ Google Sheets連携が正常に動作しています")

        # テストデータの作成
        from modules.safety_checker import ConversationResult, SafetyStatus
        test_result = ConversationResult(
            timestamp=datetime.now().isoformat(),
            duration=120.5,
            user_responses=["元気です", "はい、薬も飲んでいます"],
            ai_responses=["それは良かったです", "お薬忘れずに飲んでいて偉いですね"],
            safety_status=SafetyStatus.SAFE,
            emotion_score=0.8,
            keywords=["元気", "薬"],
            summary="体調良好で薬も服用中",
            needs_followup=False
        )

        # テスト記録の追加
        if manager.record_conversation(test_result, "テストユーザー"):
            print("✅ テスト記録の追加に成功しました")
        else:
            print("❌ テスト記録の追加に失敗しました")

        # 最近の記録取得テスト
        records = manager.get_recent_records(7)
        print(f"📋 過去7日間の記録: {len(records)}件")

    else:
        print("❌ Google Sheets連携が利用できません")
        print("💡 設定手順:")
        print("  1. Google Cloud Console でサービスアカウントを作成")
        print("  2. credentials/google_service_account.json に認証ファイルを配置")
        print("  3. .env に GOOGLE_SPREADSHEET_ID を設定")

if __name__ == "__main__":
    test_google_sheets_connection()