"""
メール通知システム (Gmail API + OAuth2)
リアルタイム会話の結果を踏まえ、家族へセキュアに通知を送信する
"""

import base64
import os
from datetime import datetime
from email.mime.text import MIMEText
from pathlib import Path
from typing import List, Optional, Tuple

from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from .logger import get_logger
from .safety_checker import ConversationResult, SafetyStatus
from .emotion_analyzer import EmotionAnalysis, EmotionCategory

logger = get_logger(__name__)

SCOPES = ["https://www.googleapis.com/auth/gmail.send"]


class EmailNotifier:
    """OAuth 認証を用いた Gmail 通知クラス"""

    def __init__(self) -> None:
        self.sender_email = os.getenv("GMAIL_USER", "")
        self.family_emails = self._parse_family_emails()
        self.client_secret_path = Path(
            os.getenv("GMAIL_CLIENT_SECRET_PATH", "data/credentials.json")
        )
        self.token_path = Path(os.getenv("GMAIL_TOKEN_PATH", "data/token.json"))

        self.service = None
        self.creds = self._load_credentials()
        if self.creds:
            try:
                self.service = build("gmail", "v1", credentials=self.creds)
                logger.info("メール通知システムが初期化されました")
            except Exception as exc:  # noqa: BLE001
                logger.error(f"Gmail API 初期化に失敗しました: {exc}")
                self.service = None
        else:
            logger.warning("メール通知の設定が不完全です")

    def _parse_family_emails(self) -> List[str]:
        raw = os.getenv("FAMILY_EMAILS", "")
        return [email.strip() for email in raw.split(",") if email.strip()]

    def _load_credentials(self) -> Optional[Credentials]:
        if not self.sender_email:
            logger.warning("GMAIL_USER が設定されていません")
            return None

        if not self.family_emails:
            logger.warning("FAMILY_EMAILS が設定されていません")
            return None

        creds: Optional[Credentials] = None
        if self.token_path.exists():
            creds = Credentials.from_authorized_user_file(
                str(self.token_path), SCOPES
            )

        try:
            if creds and not creds.valid:
                if creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    creds = None
            if not creds:
                if not self.client_secret_path.exists():
                    logger.warning("Gmail OAuth クライアントシークレットが見つかりません")
                    return None
                flow = InstalledAppFlow.from_client_secrets_file(
                    str(self.client_secret_path), SCOPES
                )
                creds = flow.run_local_server(port=0)
                self.token_path.parent.mkdir(parents=True, exist_ok=True)
                with self.token_path.open("w", encoding="utf-8") as token_file:
                    token_file.write(creds.to_json())
            return creds
        except RefreshError as exc:
            logger.error(f"Gmail トークンの更新に失敗しました: {exc}")
            return None
        except Exception as exc:  # noqa: BLE001
            logger.error(f"Gmail 認証処理でエラーが発生しました: {exc}")
            return None

    def is_available(self) -> bool:
        return self.service is not None

    def should_notify(
        self, conversation_result: ConversationResult, emotion_analysis: EmotionAnalysis
    ) -> Tuple[bool, str]:
        reasons: List[str] = []

        if conversation_result.safety_status == SafetyStatus.EMERGENCY:
            reasons.append("緊急状況が検知されました")
        elif conversation_result.safety_status == SafetyStatus.NEEDS_ATTENTION:
            reasons.append("要注意の状況が確認されました")

        if emotion_analysis.category in (
            EmotionCategory.NEGATIVE,
            EmotionCategory.ANXIOUS,
            EmotionCategory.DEPRESSED,
        ):
            reasons.append("感情状態がネガティブ方向です")

        if emotion_analysis.overall_score < -0.5:
            reasons.append(
                f"感情スコアが低下しています（{emotion_analysis.overall_score:.2f}）"
            )

        if conversation_result.needs_followup:
            reasons.append("フォローアップが必要と判定されました")

        return bool(reasons), " / ".join(reasons)

    def send_notification(
        self,
        conversation_result: ConversationResult,
        emotion_analysis: EmotionAnalysis,
        user_name: str = "利用者",
    ) -> bool:
        if not self.is_available():
            logger.warning("メール通知機能が利用できません")
            return False

        should_notify, reason = self.should_notify(conversation_result, emotion_analysis)
        if not should_notify:
            logger.info("通知条件を満たさないためメール送信をスキップします")
            return True

        try:
            subject, body = self._create_email_content(
                conversation_result, emotion_analysis, user_name, reason
            )
            for recipient in self.family_emails:
                message = self._build_message(subject, body, recipient)
                self._send_via_gmail_api(message)
                logger.info(f"通知メールを送信しました: {recipient}")
            return True
        except HttpError as exc:
            logger.error(f"Gmail API エラー: {exc}")
            return False
        except Exception as exc:  # noqa: BLE001
            logger.error(f"メール送信エラー: {exc}")
            return False

    def _build_message(self, subject: str, body: str, recipient: str) -> MIMEText:
        message = MIMEText(body, "plain", "utf-8")
        message["to"] = recipient
        message["from"] = self.sender_email
        message["subject"] = subject
        return message

    def _send_via_gmail_api(self, message: MIMEText) -> None:
        raw_bytes = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
        self.service.users().messages().send(
            userId="me", body={"raw": raw_bytes}
        ).execute()

    def _create_email_content(
        self,
        conversation_result: ConversationResult,
        emotion_analysis: EmotionAnalysis,
        user_name: str,
        reason: str,
    ) -> Tuple[str, str]:
        timestamp = datetime.fromisoformat(conversation_result.timestamp)
        date_str = timestamp.strftime("%Y年%m月%d日 %H:%M")

        if conversation_result.safety_status == SafetyStatus.EMERGENCY:
            subject = f"【緊急】{user_name}の安否確認"
            urgency = "🚨"
        elif conversation_result.safety_status == SafetyStatus.NEEDS_ATTENTION:
            subject = f"【要注意】{user_name}の安否確認"
            urgency = "⚠️"
        else:
            subject = f"【通知】{user_name}の安否状況"
            urgency = "💙"

        body_lines = [
            f"{urgency} {user_name}の安否確認レポート",
            "",
            "■ 基本情報",
            f"・日時: {date_str}",
            f"・会話時間: {conversation_result.duration / 60:.1f}分",
            f"・安否ステータス: {conversation_result.safety_status.value}",
            "",
            "■ 感情分析結果",
            f"・感情カテゴリ: {emotion_analysis.category.value}",
            f"・感情スコア: {emotion_analysis.overall_score:.2f}",
            "",
            "■ 通知理由",
            reason or "特になし",
            "",
            "■ 会話要約",
            conversation_result.summary,
            "",
            "■ ユーザー発言 (最大3件)",
        ]

        if conversation_result.user_responses:
            for idx, sentence in enumerate(conversation_result.user_responses[:3], 1):
                body_lines.append(f"  {idx}. {sentence}")
        else:
            body_lines.append("  （発言なし）")

        body_lines.extend(
            [
                "",
                "■ 備考",
                "本メールは高齢者向け安否確認システムから自動送信されています。",
                "詳しい記録は共有中の Google シートをご確認ください。",
                "",
                f"送信日時: {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}",
            ]
        )

        return subject, "\n".join(body_lines)

    def send_test_notification(self, user_name: str = "テストユーザー") -> bool:
        if not self.is_available():
            logger.warning("メール通知機能が利用できません")
            return False

        try:
            subject = f"【テスト】{user_name}の安否確認"
            body = "これはメール通知機能のテスト送信です。"
            message = self._build_message(subject, body, self.sender_email)
            self._send_via_gmail_api(message)
            logger.info("テスト通知メールを送信しました")
            return True
        except Exception as exc:  # noqa: BLE001
            logger.error(f"テストメール送信エラー: {exc}")
            return False

    def get_notification_status(self) -> dict:
        return {
            "enabled": self.is_available(),
            "sender_email": self.sender_email,
            "family_email_count": len(self.family_emails),
        }

# 使用例とテスト用の関数
def test_email_notification():
    """メール通知システムのテスト"""
    print("メール通知システムのテストを開始...")

    notifier = EmailNotifier()

    # 設定状況の確認
    status = notifier.get_notification_status()
    print(f"📧 メール通知設定状況:")
    print(f"  ・機能有効: {status['enabled']}")
    print(f"  ・送信者設定: {status['sender_email']}")
    print(f"  ・家族メール数: {status['family_email_count']}")

    if notifier.is_available():
        print("✅ メール通知機能が利用可能です")

        # テストメール送信
        if input("テストメールを送信しますか？ (y/N): ").lower() == 'y':
            if notifier.send_test_notification():
                print("✅ テストメールの送信に成功しました")
            else:
                print("❌ テストメールの送信に失敗しました")
    else:
        print("❌ メール通知機能が利用できません")
        print("💡 設定手順:")
        print("  1. .env に以下の項目を設定:")
        print("     - GMAIL_USER=送信者のメールアドレス")
        print("     - GOOGLE_APPLICATION_CREDENTIALS=Google サービスアカウント認証ファイルのパス")
        print("     - FAMILY_EMAILS=家族のメールアドレス（カンマ区切り）")
        print("  2. Google Cloud Console で Gmail API を有効化し、サービスアカウントを作成")
        print("  3. サービスアカウントの秘密鍵を JSON 形式で認証ファイルとして保存")

if __name__ == "__main__":
    test_email_notification()