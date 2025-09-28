"""
リアルタイム音声処理モジュール
OpenAI Realtime APIを使用した高品質な音声会話システム
"""

import asyncio
import json
import base64
import websockets
import pyaudio
import wave
import os
import time
from typing import Optional, Callable
from dataclasses import dataclass
from .config import Config
from .logger import get_logger

logger = get_logger(__name__)

@dataclass
class AudioConfig:
    """音声設定"""
    format: int = pyaudio.paInt16
    channels: int = 1
    rate: int = 24000
    chunk: int = 1024
    input_device_index: Optional[int] = None
    output_device_index: Optional[int] = None

class RealtimeAudioHandler:
    """リアルタイム音声処理クラス"""

    def __init__(self, audio_config: Optional[AudioConfig] = None):
        self.audio_config = audio_config or AudioConfig()
        self.websocket = None
        self.audio = pyaudio.PyAudio()
        self.is_connected = False
        self.is_recording = False
        self.is_playing = False

        # コールバック関数
        self.on_transcription: Optional[Callable[[str], None]] = None
        self.on_response_start: Optional[Callable[[], None]] = None
        self.on_response_end: Optional[Callable[[], None]] = None
        self.on_error: Optional[Callable[[str], None]] = None

        # 音声ストリーム
        self.input_stream = None
        self.output_stream = None

        # 応答管理
        self.response_in_progress = False
        self.last_speech_time = 0  # レート制限用
        self.awaiting_audio_delay = False
        self.speak_delay_seconds = 1.0  # AI音声再生前の待機時間
        self.response_cooldown_until = 0.0
        self.current_response_id: Optional[str] = None
        self.suppress_audio_output = False

        # セッション設定
        self.session_config = {
            "modalities": ["audio", "text"],
            "instructions": self._load_conversation_instructions(),
            "voice": "shimmer",
            "input_audio_format": "pcm16",
            "output_audio_format": "pcm16",
            "input_audio_transcription": {
                "model": "whisper-1",
                "language": "ja"
            },
            "turn_detection": {
                "type": "server_vad",
                "threshold": 0.75,
                "prefix_padding_ms": 300,
                "silence_duration_ms": 900
            },
            "temperature": 0.7,
            "max_response_output_tokens": 100
        }

    def _load_conversation_instructions(self) -> str:
        """会話指示を読み込み"""
        return """あなたは高齢者向けの安否確認AIアシスタントです。

【重要な指針】
- 親しみやすく、優しい話し方で接してください
- 簡潔で分かりやすい言葉を使ってください
- 相手の気持ちに寄り添い、無理に話を続けさせないでください
- 体調や気分について自然に聞いてください
- 必要に応じて家族や医療機関への連絡を提案してください
- ゆっくり落ち着いた口調で、短い間を置きながら話してください
- 相手の発話が終わるまで必ず待ち、重ならないようにしてください
- 応答は必ず日本語で、1〜2文以内にまとめてください
- 同じ質問を繰り返さず、聞き返す場合は理由を添えてください

【会話の流れ】
1. 時間に応じた自然な挨拶
2. 体調・気分の確認
3. 簡単な日常会話
4. 必要に応じたサポートの提案
5. 自然な会話の終了

常に相手のペースに合わせ、押し付けがましくならないよう注意してください。"""

    async def start_realtime_session(self) -> bool:
        """Realtime APIセッション開始"""
        try:
            logger.info("リアルタイムAPIセッションを開始...")

            # WebSocket接続
            uri = "wss://api.openai.com/v1/realtime?model=gpt-4o-realtime-preview-2024-10-01"
            headers = {
                "Authorization": f"Bearer {Config.OPENAI_API_KEY}",
                "OpenAI-Beta": "realtime=v1"
            }

            self.websocket = await websockets.connect(uri, additional_headers=headers)
            logger.info("WebSocket接続成功")

            # セッション設定送信
            await self.websocket.send(json.dumps({
                "type": "session.update",
                "session": self.session_config
            }))

            self.is_connected = True
            logger.info("リアルタイムセッション開始完了")
            return True

        except Exception as e:
            logger.error(f"リアルタイムセッション開始エラー: {e}")
            if self.on_error:
                self.on_error(f"接続エラー: {str(e)}")
            return False

    async def stream_audio_conversation(self):
        """リアルタイム音声会話処理"""
        if not self.is_connected:
            logger.error("セッションが開始されていません")
            return

        try:
            # 音声ストリーム初期化
            self._initialize_audio_streams()

            # 単一タスクで音声処理とメッセージ受信を並行実行
            audio_task = asyncio.create_task(self._capture_and_send_audio())

            logger.info("音声会話ストリーミング開始")

            # メインループ: WebSocketメッセージ受信と音声処理
            try:
                async for message in self.websocket:
                    data = json.loads(message)
                    await self._handle_api_response(data)

                    # 接続が切れた場合の処理
                    if not self.is_connected:
                        break

            except websockets.exceptions.ConnectionClosed:
                logger.info("WebSocket接続が閉じられました")
            finally:
                # 音声タスクをキャンセル
                audio_task.cancel()
                try:
                    await audio_task
                except asyncio.CancelledError:
                    pass

        except Exception as e:
            logger.error(f"音声会話エラー: {e}")
            if self.on_error:
                self.on_error(f"音声会話エラー: {str(e)}")
        finally:
            await self.stop_conversation()

    async def _capture_and_send_audio(self):
        """音声入力をキャプチャしてAPIに送信"""
        self.is_recording = True
        logger.info("🎤 音声入力開始")

        audio_chunks_sent = 0
        try:
            while self.is_connected and self.is_recording:
                # 音声データを読み取り
                audio_data = self.input_stream.read(self.audio_config.chunk, exception_on_overflow=False)

                # 音声データのサイズをチェック
                if len(audio_data) == 0:
                    logger.warning("⚠️ 空の音声データを検出")
                    continue

                # Base64エンコード
                audio_b64 = base64.b64encode(audio_data).decode('utf-8')

                # APIに送信
                message = {
                    "type": "input_audio_buffer.append",
                    "audio": audio_b64
                }

                await self.websocket.send(json.dumps(message))
                audio_chunks_sent += 1

                # 10秒ごとにデバッグ情報を出力
                if audio_chunks_sent % 100 == 0:  # より頻繁にログ出力
                    logger.info(f"📡 音声チャンク送信済み: {audio_chunks_sent}")

                # 適度な間隔で送信（レート制限を回避）
                await asyncio.sleep(0.01)  # 10ms間隔に戻す

        except Exception as e:
            logger.error(f"音声キャプチャエラー: {e}")
        finally:
            self.is_recording = False
            logger.info(f"🔇 音声入力終了 (送信チャンク数: {audio_chunks_sent})")

    async def _commit_audio_buffer(self):
        """音声バッファをコミットして転写を開始"""
        try:
            commit_message = {
                "type": "input_audio_buffer.commit"
            }
            await self.websocket.send(json.dumps(commit_message))
            logger.info("🔄 音声バッファコミット送信")
        except Exception as e:
            # バッファが小さすぎる場合は警告レベルで処理
            if "buffer too small" in str(e).lower():
                logger.warning(f"⚠️ 音声バッファが小さすぎます: {e}")
            else:
                logger.error(f"音声バッファコミットエラー: {e}")

    async def _generate_response(self, user_text: str):
        """ユーザー音声認識後の応答生成"""
        try:
            if self.response_in_progress:
                logger.warning("⚠️ 応答処理中のため新しい応答をスキップ")
                return

            response_payload = {
                "type": "response.create",
                "response": {
                    "instructions": (
                        "次の内容に日本語で1〜2文、ゆっくり落ち着いた調子で返答してください。"
                        "重複した質問は避け、共感を示しつつ会話を続けてください。"
                        "内容: " + user_text
                    ),
                    "modalities": ["audio", "text"]
                }
            }

            now = time.time()
            if now < self.response_cooldown_until:
                wait_duration = self.response_cooldown_until - now
                logger.info(f"⏳ 応答まで待機: {wait_duration:.2f}秒")
                await asyncio.sleep(wait_duration)

            await self.websocket.send(json.dumps(response_payload))
            logger.info("🤖 応答生成をトリガー")
        except Exception as e:
            logger.error(f"応答生成エラー: {e}")

    async def _trigger_response_after_speech(self):
        """音声検知終了後に応答を直接トリガー"""
        import time
        current_time = time.time()

        if self.response_in_progress:
            logger.warning("⚠️ 応答処理中のため新しい応答をスキップ")
            return

        # レート制限：前回の音声処理から3秒未満の場合はスキップ
        if current_time - self.last_speech_time < 3.0:
            logger.warning("⚠️ レート制限のため応答をスキップ（3秒待機）")
            return

        self.last_speech_time = current_time

        try:
            # 参考コードのアプローチ：直接応答生成をトリガー
            response_payload = {
                "type": "response.create",
                "response": {
                    "instructions": "直前の発話を踏まえ、日本語で1 〜2文以内の短い応答を行ってください。重複質問は避け、必要なら共感を添えてください。",
                    "modalities": ["audio", "text"]
                }
            }
            await self.websocket.send(json.dumps(response_payload))
            logger.info("🗣️ 音声検知後の応答生成をトリガー")
        except Exception as e:
            logger.error(f"音声検知後応答エラー: {e}")

    async def _generate_fallback_response(self):
        """音声認識失敗時のフォールバック応答"""
        if self.response_in_progress:
            logger.warning("⚠️ 応答処理中のため聞き返しをスキップ")
            return

        try:
            response_payload = {
                "type": "response.create",
                "response": {
                    "instructions": "ユーザーが話しましたが、音声が聞き取れませんでした。「すみません、もう一度おっしゃっていただけますか？」と優しく聞き返してください。",
                    "modalities": ["audio", "text"]
                }
            }
            await self.websocket.send(json.dumps(response_payload))
            logger.info("🔄 聞き返し応答を生成")
        except Exception as e:
            logger.error(f"フォールバック応答エラー: {e}")

    async def _handle_api_response(self, data: dict):
        """APIレスポンスを処理"""
        message_type = data.get("type")

        # すべてのメッセージタイプをログ出力（デバッグ用）
        logger.info(f"🔍 API応答: {message_type}")

        try:
            if message_type == "session.created":
                logger.info("セッション作成完了")

            elif message_type == "input_audio_buffer.speech_started":
                logger.info("🎤 音声入力検知開始")
                self.last_speech_time = time.time()

            elif message_type == "input_audio_buffer.speech_stopped":
                logger.info("🔇 音声入力検知停止")

            elif message_type == "conversation.item.input_audio_transcription.completed":
                transcript = data.get("transcript", "")
                logger.info(f"📝 音声認識結果: '{transcript}'")
                if transcript and self.on_transcription:
                    self.on_transcription(transcript)
                    # 応答生成はセルフコールバック側で制御
                elif not transcript:
                    logger.warning("⚠️ 空の音声認識結果")

            elif message_type == "conversation.item.input_audio_transcription.failed":
                error = data.get("error", {})
                logger.error(f"❌ 音声認識失敗: {error}")
                # 認識失敗でも応答を生成（聞き返し）
                await self._generate_fallback_response()

            elif message_type == "response.audio.delta":
                # 音声出力データを再生
                audio_data = data.get("delta")
                if audio_data:
                    logger.debug("🔊 音声データ受信中...")
                    await self._play_audio_delta(audio_data)

            elif message_type == "response.audio_transcript.delta":
                # テキスト応答の部分更新（ログ用）
                text_delta = data.get("delta", "")
                if text_delta:
                    logger.debug(f"応答テキスト: {text_delta}")

            elif message_type == "response.created":
                logger.info("🎵 応答作成開始")
                self.response_in_progress = True
                self.awaiting_audio_delay = True
                self.suppress_audio_output = False
                self.current_response_id = data.get("response", {}).get("id")

            elif message_type == "response.done":
                logger.info("応答完了")
                self.response_in_progress = False
                self.response_cooldown_until = time.time() + 3.0
                self.current_response_id = None
                self.suppress_audio_output = False
                if self.on_response_end:
                    self.on_response_end()

            elif message_type == "error":
                error_msg = data.get("error", {}).get("message", "不明なエラー")
                logger.error(f"API Error: {error_msg}")
                if self.on_error:
                    self.on_error(error_msg)

            else:
                logger.debug(f"未処理のメッセージタイプ: {message_type}")

        except Exception as e:
            logger.error(f"レスポンス処理エラー: {e}")

    async def _cancel_active_response(self):
        """進行中の応答をキャンセル"""
        if not self.current_response_id:
            return

        try:
            cancel_payload = {
                "type": "response.cancel",
                "response": {
                    "id": self.current_response_id
                }
            }
            await self.websocket.send(json.dumps(cancel_payload))
            logger.info("🛑 進行中の応答をキャンセル")
            self.suppress_audio_output = True
        except Exception as e:
            logger.error(f"応答キャンセルエラー: {e}")

    async def _play_audio_delta(self, audio_b64: str):
        """音声データの再生"""
        try:
            audio_data = base64.b64decode(audio_b64)

            if self.awaiting_audio_delay:
                await asyncio.sleep(self.speak_delay_seconds)
                self.awaiting_audio_delay = False

            if not self.suppress_audio_output and self.output_stream:
                self.output_stream.write(audio_data)

        except Exception as e:
            logger.error(f"音声再生エラー: {e}")


    def _initialize_audio_streams(self):
        """音声ストリームの初期化"""
        try:
            # 入力ストリーム（マイク）
            self.input_stream = self.audio.open(
                format=self.audio_config.format,
                channels=self.audio_config.channels,
                rate=self.audio_config.rate,
                input=True,
                input_device_index=self.audio_config.input_device_index,
                frames_per_buffer=self.audio_config.chunk
            )

            # 出力ストリーム（スピーカー）
            self.output_stream = self.audio.open(
                format=self.audio_config.format,
                channels=self.audio_config.channels,
                rate=self.audio_config.rate,
                output=True,
                output_device_index=self.audio_config.output_device_index,
                frames_per_buffer=self.audio_config.chunk
            )

            logger.info("音声ストリーム初期化完了")

        except Exception as e:
            logger.error(f"音声ストリーム初期化エラー: {e}")
            raise

    async def send_text_message(self, text: str):
        """テキストメッセージをAPIに送信"""
        if not self.is_connected:
            logger.error("セッションが開始されていません")
            return

        try:
            message = {
                "type": "conversation.item.create",
                "item": {
                    "type": "message",
                    "role": "user",
                    "content": [{
                        "type": "input_text",
                        "text": text
                    }]
                }
            }

            await self.websocket.send(json.dumps(message))

            # レスポンス生成をトリガー
            await self.websocket.send(json.dumps({"type": "response.create"}))

            logger.info(f"テキストメッセージ送信: {text}")

        except Exception as e:
            logger.error(f"テキストメッセージ送信エラー: {e}")

    async def stop_conversation(self):
        """会話を停止"""
        logger.info("音声会話を停止中...")

        self.is_connected = False
        self.is_recording = False
        self.is_playing = False

        # 音声ストリームを停止
        if self.input_stream:
            self.input_stream.stop_stream()
            self.input_stream.close()
            self.input_stream = None

        if self.output_stream:
            self.output_stream.stop_stream()
            self.output_stream.close()
            self.output_stream = None

        # WebSocket接続を閉じる
        if self.websocket:
            await self.websocket.close()
            self.websocket = None

        logger.info("音声会話停止完了")

    async def generate_initial_greeting(self):
        """初期挨拶を音声で生成"""
        try:
            greeting_payload = {
                "type": "response.create",
                "response": {
                    "instructions": "こんにちは。今日の調子はいかがですか？話しかけてください。",
                    "modalities": ["audio", "text"]
                }
            }
            await self.websocket.send(json.dumps(greeting_payload))
            logger.info("👋 初期挨拶を音声で生成")
        except Exception as e:
            logger.error(f"初期挨拶エラー: {e}")

    def set_callbacks(self,
                     on_transcription: Optional[Callable[[str], None]] = None,
                     on_response_start: Optional[Callable[[], None]] = None,
                     on_response_end: Optional[Callable[[], None]] = None,
                     on_error: Optional[Callable[[str], None]] = None):
        """コールバック関数を設定"""
        if on_transcription:
            self.on_transcription = on_transcription
        if on_response_start:
            self.on_response_start = on_response_start
        if on_response_end:
            self.on_response_end = on_response_end
        if on_error:
            self.on_error = on_error

    def list_audio_devices(self):
        """利用可能な音声デバイスを一覧表示"""
        logger.info("=== 音声デバイス一覧 ===")
        for i in range(self.audio.get_device_count()):
            info = self.audio.get_device_info_by_index(i)
            logger.info(f"Device {i}: {info['name']} (入力: {info['maxInputChannels']}, 出力: {info['maxOutputChannels']})")

    def __del__(self):
        """デストラクタ"""
        if hasattr(self, 'audio') and self.audio:
            self.audio.terminate()


# 使用例
async def example_usage():
    """使用例"""
    handler = RealtimeAudioHandler()

    # コールバック設定
    def on_transcript(text):
        print(f"認識されたテキスト: {text}")

    def on_error(error):
        print(f"エラー: {error}")

    handler.set_callbacks(
        on_transcription=on_transcript,
        on_error=on_error
    )

    # セッション開始
    if await handler.start_realtime_session():
        # 挨拶メッセージ送信
        await handler.send_text_message("こんにちは。今日の調子はいかがですか？")

        # 音声会話開始
        await handler.stream_audio_conversation()


if __name__ == "__main__":
    asyncio.run(example_usage())