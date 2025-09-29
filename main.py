#!/usr/bin/env python3
"""
高齢者向けリアルタイム会話システム - 改訂版

OpenAI Realtime API を利用した音声会話を中心に、感情分析・Google シート記録・メール通知までを
1本のフローにまとめたエントリーポイント。
"""

import asyncio
import os
import signal
import sys
import time
from datetime import datetime
from typing import List

from modules.config import Config
from modules.logger import get_logger
from modules.audio_handler import RealtimeAudioHandler
from modules.emotion_analyzer import EmotionRecordManager
from modules.safety_checker import ConversationResult, SafetyStatus
from modules.google_sheets import GoogleSheetsManager
from modules.email_notifier import EmailNotifier

logger = get_logger(__name__)


class RealtimeCareApp:
    """リアルタイム会話を統括する小さめのアプリケーション層"""

    END_COMMANDS = [
        "終了",
        "終わり",
        "おわり",
        "おしまい",
        "さようなら",
        "バイバイ",
        "また今度",
        "またね",
        "やめる",
        "ストップ",
    ]

    def __init__(self) -> None:
        if not Config.validate_config():
            raise RuntimeError("環境変数の設定が不足しています。Config.validate_config() を確認してください。")

        self.user_name = os.getenv("CARE_USER_NAME", "利用者")
        self.running = False
        self.handler = RealtimeAudioHandler()
        self.emotion_manager = EmotionRecordManager()
        self.google_sheets = GoogleSheetsManager()
        self.email_notifier = EmailNotifier()

        self.user_messages: List[str] = []
        self.ai_messages: List[str] = []
        self._conversation_start: float = 0.0

    async def run(self) -> None:
        """リアルタイム会話を開始し、終了後に記録処理まで行う"""
        self._setup_callbacks()

        logger.info("リアルタイム会話セッションを初期化します")
        if not await self.handler.start_realtime_session():
            print("❌ リアルタイムAPI接続に失敗しました")
            return

        greeting = self._build_time_greeting()
        self.ai_messages.append(greeting)

        print("🎙️ リアルタイム会話を開始します。終了したい場合は『終わり』などのキーワードを話してください。\n")
        print(f"🤖 AI: {greeting}\n")

        await self.handler.send_text_message(greeting)

        self.running = True
        self._conversation_start = time.time()

        try:
            while self.running:
                try:
                    await self.handler.stream_audio_conversation()
                    break  # 正常に終了したらループを抜ける
                except Exception as exc:  # noqa: BLE001 - ログ目的で広めに捕捉
                    logger.error(f"音声会話中にエラーが発生しました: {exc}")
                    print(f"⚠️ 音声会話中にエラーが発生しました: {exc}")
                    await asyncio.sleep(1)
        finally:
            await self.handler.stop_conversation()
            await self._finalize_if_needed()

    def _setup_callbacks(self) -> None:
        """RealtimeAudioHandler にコールバックを設定"""

        async def queue_response(text: str) -> None:
            try:
                await self.handler._generate_response(text)  # pylint: disable=protected-access
            except Exception as exc:  # noqa: BLE001
                logger.error(f"応答生成に失敗しました: {exc}")

        def on_transcription(text: str) -> None:
            self.user_messages.append(text)
            logger.info(f"ユーザー: {text}")

            if self._is_end_command(text):
                self.running = False
                asyncio.create_task(self.handler.stop_conversation())
                return

            asyncio.create_task(queue_response(text))

        def on_error(error: str) -> None:
            logger.error(f"音声エラー: {error}")
            print(f"⚠️ 音声エラー: {error}")

        self.handler.set_callbacks(
            on_transcription=on_transcription,
            on_error=on_error,
        )

    async def _finalize_if_needed(self) -> None:
        """会話が行われていれば感情分析や通知処理を実施"""
        if not self.user_messages and len(self.ai_messages) <= 1:
            print("📝 会話が記録されなかったため、後処理をスキップします")
            return

        duration = max(time.time() - self._conversation_start, 0.0)
        result = self._build_conversation_result(duration)

        try:
            emotion_analysis, conv_id = self.emotion_manager.process_conversation(result)
            self._display_result(result, emotion_analysis)
            self._record_to_google_sheets(result)
            self._send_email_notification(result, emotion_analysis)

            if result.safety_status == SafetyStatus.EMERGENCY:
                logger.warning("🚨 緊急状況を検知しました")
                print("🚨 速やかにご家族への連絡をご検討ください")
            elif result.needs_followup:
                logger.info("⚠️ フォローアップが推奨されます")
                print("⚠️ フォローアップが必要な可能性があります")

            logger.info(f"会話記録を保存しました (ID: {conv_id})")
        except Exception as exc:  # noqa: BLE001
            logger.error(f"会話結果の処理に失敗しました: {exc}")
            print(f"⚠️ 会話結果の処理中にエラーが発生しました: {exc}")

    def _display_result(self, result: ConversationResult, emotion_analysis) -> None:
        print("\n" + "=" * 60)
        print(f"📊 会話結果 - {self.user_name}")
        print("=" * 60)
        print(f"🕐 実行時刻: {result.timestamp}")
        print(f"⏱️ 所要時間: {result.duration:.1f}秒")
        print(f"🏥 安否ステータス: {result.safety_status.value}")
        print(f"😊 感情カテゴリ: {emotion_analysis.category.value}")
        print(f"📈 感情スコア: {emotion_analysis.overall_score:.2f}")
        print(f"🔍 信頼度: {emotion_analysis.confidence:.2f}")
        print(f"🔑 検出キーワード: {', '.join(result.keywords) if result.keywords else 'なし'}")
        print(f"📝 要約: {result.summary}")
        print("=" * 60)

    def _record_to_google_sheets(self, result: ConversationResult) -> None:
        try:
            if self.google_sheets.is_available():
                if self.google_sheets.record_conversation(result, self.user_name):
                    print("📊 Googleシートに記録を保存しました")
                else:
                    print("⚠️ Googleシートへの保存に失敗しました")
        except Exception as exc:  # noqa: BLE001
            logger.error(f"Googleシート記録エラー: {exc}")
            print(f"⚠️ Googleシート記録でエラーが発生しました: {exc}")

    def _send_email_notification(self, result: ConversationResult, emotion_analysis) -> None:
        try:
            if self.email_notifier.is_available():
                should_notify, reason = self.email_notifier.should_notify(result, emotion_analysis)
                if should_notify:
                    print(f"📧 メール通知を送信中... (理由: {reason})")
                    if self.email_notifier.send_notification(result, emotion_analysis, self.user_name):
                        print("✅ 家族にメール通知を送信しました")
                    else:
                        print("❌ メール通知の送信に失敗しました")
        except Exception as exc:  # noqa: BLE001
            logger.error(f"メール通知エラー: {exc}")
            print(f"⚠️ メール通知でエラーが発生しました: {exc}")

    def _build_conversation_result(self, duration: float) -> ConversationResult:
        safety_status = self._determine_safety_status()
        emotion_score = self._calculate_emotion_score()
        keywords = self._extract_keywords()
        summary = self._generate_summary(emotion_score)

        return ConversationResult(
            timestamp=datetime.now().isoformat(),
            duration=duration,
            user_responses=self.user_messages.copy(),
            ai_responses=self.ai_messages.copy(),
            safety_status=safety_status,
            emotion_score=emotion_score,
            keywords=keywords,
            summary=summary,
            needs_followup=safety_status in (SafetyStatus.NEEDS_ATTENTION, SafetyStatus.EMERGENCY),
        )

    def _determine_safety_status(self) -> SafetyStatus:
        if not self.user_messages:
            return SafetyStatus.UNKNOWN

        recent_text = " ".join(self.user_messages)
        emergency_keywords = ["助けて", "痛い", "苦しい", "具合悪い", "病院"]
        attention_keywords = ["しんどい", "疲れた", "調子悪い", "眠れない", "食欲ない"]

        if any(keyword in recent_text for keyword in emergency_keywords):
            return SafetyStatus.EMERGENCY
        if any(keyword in recent_text for keyword in attention_keywords):
            return SafetyStatus.NEEDS_ATTENTION
        return SafetyStatus.SAFE

    def _calculate_emotion_score(self) -> float:
        if not self.user_messages:
            return 0.0

        positives = ["元気", "良い", "楽しい", "嬉しい", "安心", "ありがとう"]
        negatives = ["痛い", "悪い", "しんどい", "疲れた", "心配", "不安"]
        text = " ".join(self.user_messages)
        positive_score = sum(text.count(word) for word in positives)
        negative_score = sum(text.count(word) for word in negatives)
        total_words = max(len(text.split()), 1)
        score = (positive_score - negative_score) / max(total_words * 0.1, 1)
        return max(-1.0, min(1.0, score))

    def _extract_keywords(self) -> List[str]:
        candidates = [
            "薬",
            "病院",
            "痛み",
            "食事",
            "睡眠",
            "家族",
            "運動",
            "散歩",
            "友達",
            "買い物",
            "元気",
            "疲れた",
            "楽しい",
            "心配",
        ]
        text = " ".join(self.user_messages)
        return [word for word in candidates if word in text]

    def _generate_summary(self, emotion_score: float) -> str:
        if not self.user_messages:
            return "会話応答なし"

        mood = "普通"
        if emotion_score > 0.3:
            mood = "良好"
        elif emotion_score < -0.3:
            mood = "要注意"

        return f"会話ラウンド: {len(self.user_messages)}、全体評価: {mood}"

    @staticmethod
    def _is_end_command(text: str) -> bool:
        return any(command in text for command in RealtimeCareApp.END_COMMANDS)

    def _build_time_greeting(self) -> str:
        now = datetime.now()
        hour = now.hour
        minute = now.minute

        if 6 <= hour < 12:
            prefix = "おはようございます"
        elif 12 <= hour < 18:
            prefix = "こんにちは"
        else:
            prefix = "こんばんは"

        return f"{prefix}、現在の時刻は{hour}時{minute}分です。今日のお加減はいかがでしょうか？"


async def run_app() -> None:
    app = RealtimeCareApp()
    await app.run()


def main() -> None:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, lambda: asyncio.ensure_future(cancel_tasks(loop)))
        except NotImplementedError:
            # Windows など signal ハンドラを設定できない環境もあるので無視
            pass

    try:
        loop.run_until_complete(run_app())
    except KeyboardInterrupt:
        print("\n👋 ユーザー操作により終了しました")
    finally:
        pending = asyncio.all_tasks(loop)
        for task in pending:
            task.cancel()
        loop.run_until_complete(loop.shutdown_asyncgens())
        loop.close()


async def cancel_tasks(loop: asyncio.AbstractEventLoop) -> None:
    for task in [t for t in asyncio.all_tasks(loop) if not t.done()]:
        task.cancel()
    raise KeyboardInterrupt


if __name__ == "__main__":
    main()
