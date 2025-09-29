"""
1日1回会話モジュール
OpenAI Realtime APIを使用した高齢者向け会話システム
"""

import asyncio
import json
import os
import time
from datetime import datetime
import websockets
from dotenv import load_dotenv
import pyaudio
import base64

load_dotenv()

class DailyConversation:
    def __init__(self):
        self.api_key = os.getenv('OPENAI_API_KEY')
        self.websocket = None
        self.is_connected = False
        self.conversation_active = True

        # 音声設定
        self.audio_format = pyaudio.paInt16
        self.channels = 1
        self.rate = 24000
        self.chunk = 1024
        self.audio = pyaudio.PyAudio()
        self.audio_input_stream = None
        self.audio_output_stream = None

        # プロンプト設計に基づく設定
        self.system_prompt = self._load_system_prompt()

    def _load_system_prompt(self):
        """prompt_design.mdに基づくシステムプロンプト"""
        return """あなたは高齢者の方との会話を専門とする優しいAIアシスタントです。

【会話の基本方針】
- 丁寧で親しみやすい口調で話してください
- ゆっくり話す。応答は1秒待ってから出力する
- 相手の言葉をそのまま引用・言い換えながら共感する (鸚鵡返し)
- 相槌は『うん』『そうなんですね』『それで？』など短く静かに、相手が話し終えてから
- 応答は1-2文で簡潔に。まず共感し、興味を示して話題を広げる。「はい」だけの返答は避け、具体的に反応する
- ユーザーが話している間は完全に黙り、音声を出さない
- 5秒以上沈黙した場合のみ『思い出したらゆっくりで大丈夫ですよ』とフォローする
- 会話履歴があれば直近のキーワードを1つだけ添えて話題を広げる
- 何を話したら良いかわからない状況であれば脳トレや記憶ゲームを1つ提案し、無理に押し付けない

【話題の選択】
- 天気、季節の話題
- 健康に関する軽い話題
- 昔の思い出や経験
- 家族や友人の話
- 趣味や興味のある話題
- 日常生活の出来事

【避けるべき話題】
- 政治的な内容
- 宗教的な内容
- 病気や死に関する重い話題
- 複雑な技術的説明
- ネガティブすぎる内容
"""

    async def connect_realtime_api(self):
        """Realtime APIに接続"""
        try:
            if not self.api_key or self.api_key == "your_openai_api_key_here":
                print("❌ OPENAI_API_KEYが正しく設定されていません")
                print("📝 .envファイルに実際のAPIキーを設定してください")
                return False

            # OpenAI Realtime API WebSocket endpoint
            uri = f"wss://api.openai.com/v1/realtime?model=gpt-4o-realtime-preview-2024-10-01"

            # WebSocket接続（OpenAI公式ライブラリ使用を検討）
            import ssl
            ssl_context = ssl.create_default_context()

            self.websocket = await websockets.connect(
                uri,
                ssl=ssl_context,
                subprotocols=["realtime"],
                origin="https://api.openai.com",
                additional_headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "OpenAI-Beta": "realtime=v1"
                }
            )
            self.is_connected = True

            # セッション設定
            await self._setup_session()

            # 音声ストリーム初期化
            self._setup_audio_streams()

            print("✅ Realtime API接続成功")
            return True

        except websockets.exceptions.InvalidStatusCode as e:
            if e.status_code == 401:
                print("❌ APIキーが無効です。正しいAPIキーを設定してください")
            else:
                print(f"❌ WebSocket接続エラー: {e}")
            return False
        except Exception as e:
            print(f"❌ Realtime API接続エラー: {e}")
            print("💡 APIキーの確認、インターネット接続を確認してください")
            return False

    async def _setup_session(self):
        """セッション初期設定"""
        session_config = {
            "type": "session.update",
            "session": {
                "modalities": ["text", "audio"],
                "instructions": self.system_prompt,
                "voice": "alloy",
                "input_audio_format": "pcm16",
                "output_audio_format": "pcm16",
                "input_audio_transcription": {
                    "model": "whisper-1"
                },
                "turn_detection": {
                    "type": "server_vad",
                    "threshold": 0.5,
                    "prefix_padding_ms": 300,
                    "silence_duration_ms": 5000  # 5秒沈黙検出
                }
            }
        }

        await self.websocket.send(json.dumps(session_config))

    def _setup_audio_streams(self):
        """音声ストリーム設定"""
        try:
            # マイク入力ストリーム
            self.audio_input_stream = self.audio.open(
                format=self.audio_format,
                channels=self.channels,
                rate=self.rate,
                input=True,
                frames_per_buffer=self.chunk
            )

            # スピーカー出力ストリーム
            self.audio_output_stream = self.audio.open(
                format=self.audio_format,
                channels=self.channels,
                rate=self.rate,
                output=True,
                frames_per_buffer=self.chunk
            )

            print("🎤 音声ストリーム初期化完了")
        except Exception as e:
            print(f"❌ 音声ストリーム初期化エラー: {e}")

    async def _audio_input_loop(self):
        """音声入力ループ"""
        try:
            while self.conversation_active and self.is_connected:
                # マイクから音声データを読み取り
                audio_data = self.audio_input_stream.read(self.chunk, exception_on_overflow=False)

                # Base64エンコード
                audio_base64 = base64.b64encode(audio_data).decode('utf-8')

                # Realtime APIに音声データを送信
                audio_message = {
                    "type": "input_audio_buffer.append",
                    "audio": audio_base64
                }

                await self._send_audio_data(audio_message)
                await asyncio.sleep(0.01)  # 小さな遅延

        except Exception as e:
            print(f"❌ 音声入力エラー: {e}")

    async def _send_audio_data(self, message):
        """音声データをWebSocketで送信"""
        try:
            if self.websocket and self.is_connected:
                await self.websocket.send(json.dumps(message))
        except Exception as e:
            print(f"❌ 音声データ送信エラー: {e}")

    async def start_conversation(self):
        """会話セッション開始"""
        if not self.is_connected:
            print("❌ APIに接続されていません")
            return

        print("🎤 会話開始（「終わり」「さようなら」で終了）")

        try:
            # 応答ハンドラータスクを開始
            response_task = asyncio.create_task(self._handle_responses())

            # 音声入力タスクを開始
            audio_task = asyncio.create_task(self._audio_input_loop())

            # 会話ループ
            while self.conversation_active:
                await asyncio.sleep(0.1)  # CPU負荷軽減

            # 終了処理
            response_task.cancel()
            audio_task.cancel()

        except Exception as e:
            print(f"❌ 会話中にエラー: {e}")

    async def _handle_responses(self):
        """レスポンス処理"""
        try:
            async for message in self.websocket:
                data = json.loads(message)

                if data.get("type") == "conversation.item.input_audio_transcription.completed":
                    user_text = data.get("transcript", "")
                    print(f"👤 ユーザー: {user_text}")

                    # 終了コマンドチェック
                    if self._check_exit_command(user_text):
                        await self._handle_goodbye()
                        break

                elif data.get("type") == "response.audio_transcript.done":
                    ai_text = data.get("transcript", "")
                    print(f"🤖 AI: {ai_text}")

                elif data.get("type") == "response.audio.delta":
                    # AI音声データを受信して再生
                    audio_data = data.get("delta", "")
                    if audio_data:
                        self._play_audio(audio_data)

                elif data.get("type") == "error":
                    print(f"❌ APIエラー: {data}")

        except Exception as e:
            print(f"❌ レスポンス処理エラー: {e}")

    def _play_audio(self, audio_base64):
        """受信した音声データを再生"""
        try:
            # Base64デコードして音声データを取得
            audio_data = base64.b64decode(audio_base64)

            # スピーカーに出力
            if self.audio_output_stream:
                self.audio_output_stream.write(audio_data)

        except Exception as e:
            print(f"❌ 音声再生エラー: {e}")

    def _check_exit_command(self, text):
        """終了コマンドチェック"""
        exit_commands = ["終わり", "おしまい", "さようなら", "バイバイ"]
        return any(cmd in text for cmd in exit_commands)

    async def _handle_goodbye(self):
        """終了処理"""
        # お別れメッセージを送信
        goodbye_message = {
            "type": "conversation.item.create",
            "item": {
                "type": "message",
                "role": "user",
                "content": [
                    {
                        "type": "input_text",
                        "text": "会話を終了します"
                    }
                ]
            }
        }

        await self.websocket.send(json.dumps(goodbye_message))

        # AIからの最終応答を待つ
        await asyncio.sleep(2)

        print("👋 ありがとうございました。また明日お話ししましょう。")
        self.conversation_active = False

    async def disconnect(self):
        """接続終了"""
        if self.websocket:
            await self.websocket.close()
            self.is_connected = False

        # 音声ストリーム終了
        if self.audio_input_stream:
            self.audio_input_stream.stop_stream()
            self.audio_input_stream.close()

        if self.audio_output_stream:
            self.audio_output_stream.stop_stream()
            self.audio_output_stream.close()

        if self.audio:
            self.audio.terminate()

        print("🔌 Realtime API接続終了")

async def test_conversation():
    """テスト用会話関数"""
    conversation = DailyConversation()

    # API接続
    if await conversation.connect_realtime_api():
        # 会話開始
        await conversation.start_conversation()

        # 接続終了
        await conversation.disconnect()
    else:
        print("❌ API接続に失敗しました")

if __name__ == "__main__":
    asyncio.run(test_conversation())