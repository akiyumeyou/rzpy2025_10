"""
シンプル音声会話システム
Whisper + GPT-4o + TTS
自動起動・音声のみ・UIなし
"""

import asyncio
import io
import tempfile
import pyaudio
import wave
import openai
import os
import sys
import time
import subprocess
import struct
import math
from datetime import datetime

# モジュールパスを追加
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from modules.config import Config
from modules.logger import get_logger

logger = get_logger(__name__)

class SimpleVoiceChat:
    """シンプル音声会話システム"""

    def __init__(self):
        # OpenAI設定
        self.client = openai.OpenAI(api_key=Config.OPENAI_API_KEY)

        # 音声設定
        self.chunk = 512
        self.format = pyaudio.paInt16
        self.channels = 1
        self.rate = 16000
        self.record_seconds = 0.5  # 0.5秒単位で録音

        self.audio = pyaudio.PyAudio()
        self.running = False
        self.conversation_history = []

        print("🎤 シンプル音声会話システム初期化完了")

    def detect_speech(self, audio_data) -> bool:
        """音声検知（音量ベース）"""
        # バイトデータを16bit整数に変換
        fmt = '<' + ('h' * (len(audio_data) // 2))
        audio_ints = struct.unpack(fmt, audio_data)

        # RMS計算
        sum_squares = sum(x * x for x in audio_ints)
        rms = math.sqrt(sum_squares / len(audio_ints))

        # 閾値（調整可能）
        threshold = 500
        return rms > threshold

    async def listen_for_speech(self) -> bytes:
        """音声を聞いて録音"""
        print("👂 音声を待機中... (話しかけてください)")

        stream = self.audio.open(
            format=self.format,
            channels=self.channels,
            rate=self.rate,
            input=True,
            frames_per_buffer=self.chunk
        )

        frames = []
        is_recording = False
        silence_count = 0
        max_silence = 15  # 約0.75秒の無音で終了

        try:
            while True:
                data = stream.read(self.chunk, exception_on_overflow=False)

                speech_detected = self.detect_speech(data)

                if speech_detected:
                    if not is_recording:
                        print("🎤 音声検知開始")
                        is_recording = True
                        frames = []

                    frames.append(data)
                    silence_count = 0

                elif is_recording:
                    frames.append(data)  # 無音部分も少し録音
                    silence_count += 1

                    if silence_count > max_silence:
                        print("🔇 音声検知終了")
                        break

                # 非ブロッキング処理
                await asyncio.sleep(0.01)

        finally:
            stream.stop_stream()
            stream.close()

        if frames:
            return b''.join(frames)
        return b''

    async def transcribe_audio(self, audio_data: bytes) -> str:
        """音声をテキストに変換"""
        if not audio_data:
            return ""

        try:
            print("🔄 音声認識中...")

            import io

            buffer = io.BytesIO()
            with wave.open(buffer, 'wb') as wav_file:
                wav_file.setnchannels(self.channels)
                wav_file.setsampwidth(self.audio.get_sample_size(self.format))
                wav_file.setframerate(self.rate)
                wav_file.writeframes(audio_data)

            buffer.seek(0)

            transcript = self.client.audio.transcriptions.create(
                model="whisper-1",
                file=("audio.wav", buffer, "audio/wav"),
                language="ja"
            )

            return transcript.text.strip()

        except Exception as e:
            logger.error(f"音声認識エラー: {e}")
            return ""

    async def generate_response(self, user_text: str) -> str:
        """AI応答生成"""
        try:
            print("🤖 AI応答生成中...")

            # 会話履歴に追加
            self.conversation_history.append({"role": "user", "content": user_text})

            # 履歴管理（最新20件保持）
            if len(self.conversation_history) > 20:
                self.conversation_history = self.conversation_history[-20:]

            # システムプロンプト
            system_prompt = """あなたは高齢者向けの優しい会話相手です。

【重要】
- 親しみやすく、温かい話し方
- 簡潔で分かりやすい言葉（1-2文程度）
- 相手の気持ちに寄り添う
- 体調や気分を自然に確認
- 相手のペースに合わせる

初回は軽い挨拶から始めて、徐々に安否確認につなげてください。"""

            messages = [{"role": "system", "content": system_prompt}] + self.conversation_history

            # GPT-4o応答生成
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=messages,
                max_tokens=100,
                temperature=0.8
            )

            ai_text = response.choices[0].message.content.strip()

            # 履歴に追加
            self.conversation_history.append({"role": "assistant", "content": ai_text})

            return ai_text

        except Exception as e:
            logger.error(f"AI応答エラー: {e}")
            return "すみません、よく聞こえませんでした。もう一度お話しください。"

    async def speak_text(self, text: str):
        """テキストを音声で再生"""
        try:
            print("🔊 音声生成中...")

            # TTS生成
            response = self.client.audio.speech.create(
                model="tts-1",
                voice="alloy",
                input=text,
                response_format="mp3"
            )

            # 一時ファイル保存
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_audio:
                temp_audio.write(response.content)
                temp_audio_path = temp_audio.name

            print("🔊 音声再生中...")

            # macOSのafplayで再生
            if os.system("which afplay > /dev/null 2>&1") == 0:
                process = await asyncio.create_subprocess_exec(
                    'afplay', temp_audio_path,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                await process.wait()
            else:
                # Linuxの場合はmpg123を試行
                process = await asyncio.create_subprocess_exec(
                    'mpg123', temp_audio_path,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                await process.wait()

            # 一時ファイル削除
            os.unlink(temp_audio_path)
            print("✅ 音声再生完了")

        except Exception as e:
            logger.error(f"音声再生エラー: {e}")
            print(f"❌ 音声再生エラー: {e}")

    def is_end_command(self, text: str) -> bool:
        """終了コマンド判定"""
        end_phrases = [
            "終了", "おわり", "バイバイ", "さようなら",
            "もういい", "やめる", "ストップ", "終わり",
            "また今度", "またね"
        ]
        return any(phrase in text for phrase in end_phrases)

    async def run_conversation(self):
        """会話メインループ"""
        self.running = True

        print("🌸 音声会話システム開始")
        print("💡 自動で開始します...")

        # 開始挨拶
        current_hour = datetime.now().hour
        if 6 <= current_hour < 12:
            greeting = "おはようございます。今日の調子はいかがですか？"
        elif 12 <= current_hour < 18:
            greeting = "こんにちは。今日はいかがお過ごしですか？"
        else:
            greeting = "こんばんは。今日一日お疲れさまでした。"

        print(f"🤖 AI: {greeting}")
        await self.speak_text(greeting)

        conversation_count = 0

        try:
            while self.running:
                # 音声を聞く
                audio_data = await self.listen_for_speech()

                if audio_data:
                    # 音声認識
                    user_text = await self.transcribe_audio(audio_data)

                    if user_text:
                        print(f"👤 ユーザー: {user_text}")
                        conversation_count += 1

                        # 終了コマンドチェック
                        if self.is_end_command(user_text):
                            goodbye = "お話しできて良かったです。また今度お話ししましょう。お体に気をつけてくださいね。"
                            print(f"🤖 AI: {goodbye}")
                            await self.speak_text(goodbye)
                            break

                        # AI応答生成
                        ai_response = await self.generate_response(user_text)
                        print(f"🤖 AI: {ai_response}")

                        # 音声で応答
                        await self.speak_text(ai_response)

                        # 長時間会話の場合は自然に終了提案
                        if conversation_count >= 8:
                            ending_suggestion = "たくさんお話しできて楽しかったです。今日はこのあたりでいかがでしょうか？"
                            print(f"🤖 AI: {ending_suggestion}")
                            await self.speak_text(ending_suggestion)
                            conversation_count = 0  # リセット

                    else:
                        print("⚠️ 音声が認識できませんでした")

                else:
                    print("⚠️ 音声データが取得できませんでした")

        except KeyboardInterrupt:
            print("\n🛑 Ctrl+Cで終了")
        finally:
            self.running = False
            self.audio.terminate()

async def main():
    """メイン実行"""
    print("🎤" + "="*50)
    print("  シンプル音声会話システム")
    print("  Whisper + GPT-4o + TTS")
    print("="*52 + "🎤")

    chat = SimpleVoiceChat()
    await chat.run_conversation()

    print("\n✅ 会話終了")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 システム終了")
    except Exception as e:
        print(f"❌ エラー: {e}")
        logger.error(f"システムエラー: {e}")