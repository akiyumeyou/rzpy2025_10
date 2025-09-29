"""
安否確認システムのメインロジック
リアルタイム音声会話を使った高齢者向け安否確認
"""

import asyncio
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass, asdict
from enum import Enum

from .audio_handler import RealtimeAudioHandler, AudioConfig
from .config import Config
from .logger import get_logger, ConversationLogger

logger = get_logger(__name__)
conv_logger = ConversationLogger()

class SafetyStatus(Enum):
    """安否確認ステータス"""
    UNKNOWN = "unknown"           # 未確認
    SAFE = "safe"                # 安全
    NEEDS_ATTENTION = "attention" # 要注意
    EMERGENCY = "emergency"       # 緊急

@dataclass
class ConversationResult:
    """会話結果"""
    timestamp: str
    duration: float
    user_responses: List[str]
    ai_responses: List[str]
    safety_status: SafetyStatus
    emotion_score: float  # -1.0(negative) to 1.0(positive)
    keywords: List[str]
    summary: str
    needs_followup: bool

class SafetyChecker:
    """安否確認システム"""

    def __init__(self, user_name: str = "田中さん"):
        self.user_name = user_name
        self.audio_handler = RealtimeAudioHandler()
        self.conversation_active = False
        self.start_time = None

        # 会話データ
        self.user_responses = []
        self.ai_responses = []
        self.current_transcript = ""

        # コールバック設定
        self.on_safety_status_change: Optional[Callable[[SafetyStatus], None]] = None
        self.on_conversation_complete: Optional[Callable[[ConversationResult], None]] = None

        # 音声処理コールバック設定
        self._setup_audio_callbacks()

    def _setup_audio_callbacks(self):
        """音声処理のコールバック設定"""

        def on_transcription(text: str):
            """音声認識結果の処理"""
            self.current_transcript = text
            self.user_responses.append(text)
            conv_logger.log_user_input(text)
            logger.info(f"ユーザー: {text}")

        def on_response_start():
            """AI応答開始"""
            logger.debug("AI応答開始")

        def on_response_end():
            """AI応答完了"""
            logger.debug("AI応答完了")

        def on_error(error: str):
            """エラー処理"""
            logger.error(f"音声エラー: {error}")

        self.audio_handler.set_callbacks(
            on_transcription=on_transcription,
            on_response_start=on_response_start,
            on_response_end=on_response_end,
            on_error=on_error
        )

    async def start_safety_check(self) -> ConversationResult:
        """安否確認を開始"""
        logger.info(f"安否確認開始: {self.user_name}")
        conv_logger.log_conversation_start(self.user_name)

        self.start_time = time.time()
        self.conversation_active = True
        self.user_responses.clear()
        self.ai_responses.clear()

        try:
            # リアルタイムAPI接続
            if not await self.audio_handler.start_realtime_session():
                logger.error("リアルタイムAPI接続に失敗")
                return self._create_error_result()

            # 安否確認会話の実行
            result = await self._conduct_safety_conversation()

            return result

        except Exception as e:
            logger.error(f"安否確認エラー: {e}")
            return self._create_error_result()
        finally:
            await self._cleanup()

    async def _conduct_safety_conversation(self) -> ConversationResult:
        """安否確認会話を実行"""
        logger.info("安否確認会話開始")

        try:
            # 音声会話を開始（バックグラウンドで実行）
            conversation_task = asyncio.create_task(
                self.audio_handler.stream_audio_conversation()
            )

            # 各ステップを順番に実行
            conversation_steps = [
                self._greeting_step,
                self._health_check_step,
                self._mood_check_step,
                self._daily_life_step,
                self._closing_step
            ]

            for i, step in enumerate(conversation_steps):
                logger.debug(f"ステップ {i+1}/{len(conversation_steps)} 実行中")

                try:
                    await step()

                    # ステップ間の自然な間隔
                    await asyncio.sleep(3)

                    # 緊急状況の確認
                    if self._detect_emergency():
                        logger.warning("緊急状況を検知")
                        break

                except Exception as e:
                    logger.error(f"会話ステップ {i+1} エラー: {e}")
                    continue

            # 音声会話タスクをキャンセル
            conversation_task.cancel()

        except Exception as e:
            logger.error(f"安否確認会話エラー: {e}")

        # 会話結果の分析
        return await self._analyze_conversation()

    async def _greeting_step(self):
        """挨拶ステップ"""
        current_hour = datetime.now().hour

        if 6 <= current_hour < 12:
            greeting = f"おはようございます、{self.user_name}。"
        elif 12 <= current_hour < 18:
            greeting = f"こんにちは、{self.user_name}。"
        else:
            greeting = f"こんばんは、{self.user_name}。"

        message = f"{greeting}今日の調子はいかがですか？"
        await self._send_message_and_wait(message, expected_response_time=10)

    async def _health_check_step(self):
        """体調確認ステップ"""
        # 前回の応答を分析して適切な質問を選択
        if self._contains_negative_words(self.current_transcript):
            message = "そうですか。どこか具合の悪いところはありますか？"
        else:
            message = "お薬は忘れずに飲めていますか？"

        await self._send_message_and_wait(message, expected_response_time=8)

    async def _mood_check_step(self):
        """気分確認ステップ"""
        message = "今日は何か楽しいことはありましたか？"
        await self._send_message_and_wait(message, expected_response_time=10)

    async def _daily_life_step(self):
        """日常生活確認ステップ"""
        message = "お食事はちゃんと取れていますか？"
        await self._send_message_and_wait(message, expected_response_time=8)

    async def _closing_step(self):
        """終了ステップ"""
        message = "お話しできて良かったです。何かご心配なことがあればいつでもお声かけくださいね。"
        await self._send_message_and_wait(message, expected_response_time=5)

    async def _send_message_and_wait(self, message: str, expected_response_time: int = 10):
        """メッセージを送信して応答を待機"""
        self.ai_responses.append(message)
        conv_logger.log_ai_response(message)

        # メッセージ送信
        await self.audio_handler.send_text_message(message)

        # シンプルな待機（音声会話は別途実行中）
        try:
            await asyncio.wait_for(
                self._wait_for_user_response(),
                timeout=expected_response_time
            )
        except asyncio.TimeoutError:
            logger.warning(f"ユーザー応答タイムアウト ({expected_response_time}秒)")

    async def _wait_for_user_response(self):
        """ユーザーの応答を待機（音声会話は別途実行中）"""
        initial_response_count = len(self.user_responses)

        # 新しい応答があるまで待機
        while len(self.user_responses) <= initial_response_count:
            await asyncio.sleep(0.5)
            if not self.conversation_active:
                break

    def _contains_negative_words(self, text: str) -> bool:
        """ネガティブな言葉を含むかチェック"""
        negative_words = [
            "痛い", "痛み", "具合悪い", "調子悪い", "気分悪い",
            "しんどい", "疲れた", "眠れない", "食欲ない",
            "心配", "不安", "寂しい", "悲しい"
        ]
        return any(word in text for word in negative_words)

    def _detect_emergency(self) -> bool:
        """緊急状況の検知"""
        emergency_keywords = [
            "助けて", "痛い", "苦しい", "息ができない",
            "倒れ", "転んだ", "動けない", "意識",
            "救急車", "病院", "緊急"
        ]

        recent_responses = " ".join(self.user_responses[-3:])  # 直近3つの応答
        return any(keyword in recent_responses for keyword in emergency_keywords)

    async def _analyze_conversation(self) -> ConversationResult:
        """会話を分析して結果を作成"""
        duration = time.time() - self.start_time if self.start_time else 0

        # 安否ステータスの判定
        safety_status = self._determine_safety_status()

        # 感情スコアの計算
        emotion_score = self._calculate_emotion_score()

        # キーワード抽出
        keywords = self._extract_keywords()

        # 要約生成
        summary = self._generate_summary()

        # フォローアップの必要性判定
        needs_followup = safety_status in [SafetyStatus.NEEDS_ATTENTION, SafetyStatus.EMERGENCY]

        result = ConversationResult(
            timestamp=datetime.now().isoformat(),
            duration=duration,
            user_responses=self.user_responses.copy(),
            ai_responses=self.ai_responses.copy(),
            safety_status=safety_status,
            emotion_score=emotion_score,
            keywords=keywords,
            summary=summary,
            needs_followup=needs_followup
        )

        conv_logger.log_conversation_end(duration)
        logger.info(f"安否確認完了: {safety_status.value}, 感情スコア: {emotion_score:.2f}")

        # コールバック実行
        if self.on_conversation_complete:
            self.on_conversation_complete(result)

        return result

    def _determine_safety_status(self) -> SafetyStatus:
        """安否ステータスを判定"""
        if not self.user_responses:
            return SafetyStatus.UNKNOWN

        all_responses = " ".join(self.user_responses)

        # 緊急キーワードのチェック
        if self._detect_emergency():
            return SafetyStatus.EMERGENCY

        # ネガティブな応答のチェック
        negative_count = sum(1 for response in self.user_responses
                           if self._contains_negative_words(response))

        if negative_count >= 2:
            return SafetyStatus.NEEDS_ATTENTION
        elif negative_count == 1:
            return SafetyStatus.NEEDS_ATTENTION
        else:
            return SafetyStatus.SAFE

    def _calculate_emotion_score(self) -> float:
        """感情スコアを計算（-1.0 to 1.0）"""
        if not self.user_responses:
            return 0.0

        positive_words = ["元気", "良い", "大丈夫", "楽しい", "嬉しい", "ありがとう"]
        negative_words = ["痛い", "悪い", "しんどい", "疲れた", "心配", "不安"]

        all_text = " ".join(self.user_responses)

        positive_score = sum(1 for word in positive_words if word in all_text)
        negative_score = sum(1 for word in negative_words if word in all_text)

        total_words = len(all_text.split())
        if total_words == 0:
            return 0.0

        # 正規化されたスコア
        score = (positive_score - negative_score) / max(total_words * 0.1, 1)
        return max(-1.0, min(1.0, score))

    def _extract_keywords(self) -> List[str]:
        """重要なキーワードを抽出"""
        important_keywords = [
            "薬", "病院", "医者", "痛み", "食事", "睡眠",
            "家族", "友達", "散歩", "買い物", "テレビ",
            "元気", "疲れた", "楽しい", "心配"
        ]

        all_text = " ".join(self.user_responses)
        found_keywords = [keyword for keyword in important_keywords if keyword in all_text]

        return found_keywords

    def _generate_summary(self) -> str:
        """会話の要約を生成"""
        if not self.user_responses:
            return "応答なし"

        # 簡単な要約ロジック
        response_count = len(self.user_responses)
        emotion_score = self._calculate_emotion_score()

        if emotion_score > 0.3:
            mood = "良好"
        elif emotion_score < -0.3:
            mood = "要注意"
        else:
            mood = "普通"

        return f"会話応答数: {response_count}, 全体的な調子: {mood}"

    def _create_error_result(self) -> ConversationResult:
        """エラー時の結果を作成"""
        return ConversationResult(
            timestamp=datetime.now().isoformat(),
            duration=0,
            user_responses=[],
            ai_responses=[],
            safety_status=SafetyStatus.UNKNOWN,
            emotion_score=0.0,
            keywords=[],
            summary="接続エラーにより安否確認できませんでした",
            needs_followup=True
        )

    async def _cleanup(self):
        """リソースのクリーンアップ"""
        self.conversation_active = False
        if self.audio_handler:
            await self.audio_handler.stop_conversation()

    def set_callbacks(self,
                     on_safety_status_change: Optional[Callable[[SafetyStatus], None]] = None,
                     on_conversation_complete: Optional[Callable[[ConversationResult], None]] = None):
        """コールバック関数を設定"""
        if on_safety_status_change:
            self.on_safety_status_change = on_safety_status_change
        if on_conversation_complete:
            self.on_conversation_complete = on_conversation_complete


# 使用例
async def example_safety_check():
    """安否確認の使用例"""
    checker = SafetyChecker("田中さん")

    def on_status_change(status: SafetyStatus):
        print(f"安否ステータス変更: {status.value}")

    def on_complete(result: ConversationResult):
        print(f"安否確認完了:")
        print(f"  ステータス: {result.safety_status.value}")
        print(f"  感情スコア: {result.emotion_score:.2f}")
        print(f"  要約: {result.summary}")

        if result.needs_followup:
            print("⚠️ フォローアップが必要です")

    checker.set_callbacks(
        on_safety_status_change=on_status_change,
        on_conversation_complete=on_complete
    )

    # 安否確認実行
    result = await checker.start_safety_check()
    return result


if __name__ == "__main__":
    asyncio.run(example_safety_check())