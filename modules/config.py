"""
設定管理モジュール
環境変数とアプリケーション設定を管理
"""

import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

# .envファイルを読み込み
load_dotenv()


class Config:
    """アプリケーション設定クラス"""

    # プロジェクトのルートディレクトリ
    PROJECT_ROOT = Path(__file__).parent.parent

    # OpenAI API設定
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "")

    # データベース設定
    DATABASE_PATH: str = os.getenv(
        "DATABASE_PATH", str(PROJECT_ROOT / "data" / "conversations.db")
    )

    # ログ設定
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE: str = os.getenv("LOG_FILE", str(PROJECT_ROOT / "logs" / "app.log"))

    # 音声設定
    AUDIO_SAMPLE_RATE: int = int(os.getenv("AUDIO_SAMPLE_RATE", "24000"))
    AUDIO_CHANNELS: int = int(os.getenv("AUDIO_CHANNELS", "1"))
    AUDIO_CHUNK_SIZE: int = int(os.getenv("AUDIO_CHUNK_SIZE", "1024"))

    # リアルタイムAPI設定
    REALTIME_API_URL: str = "wss://api.openai.com/v1/realtime"
    REALTIME_VOICE: str = os.getenv("REALTIME_VOICE", "shimmer")
    REALTIME_TEMPERATURE: float = float(os.getenv("REALTIME_TEMPERATURE", "0.8"))

    # 安否確認設定
    SAFETY_CHECK_TIMES: list = ["10:00", "15:00", "19:00"]  # デフォルトの確認時間
    MAX_CONVERSATION_DURATION: int = int(
        os.getenv("MAX_CONVERSATION_DURATION", "300")
    )  # 秒

    # 通知設定
    NOTIFICATION_EMAIL: str = os.getenv("NOTIFICATION_EMAIL", "")
    NOTIFICATION_PHONE: str = os.getenv("NOTIFICATION_PHONE", "")

    # Azure Speech Services設定（代替音声合成用）
    AZURE_SPEECH_KEY: str = os.getenv("AZURE_SPEECH_KEY", "")
    AZURE_SPEECH_REGION: str = os.getenv("AZURE_SPEECH_REGION", "japaneast")

    @classmethod
    def validate_config(cls) -> bool:
        """設定の検証"""
        errors = []

        if not cls.OPENAI_API_KEY:
            errors.append("OPENAI_API_KEY が設定されていません")

        if not cls.OPENAI_API_KEY.startswith("sk-"):
            errors.append("OPENAI_API_KEY の形式が正しくありません")

        # 必要なディレクトリの作成
        os.makedirs(Path(cls.DATABASE_PATH).parent, exist_ok=True)
        os.makedirs(Path(cls.LOG_FILE).parent, exist_ok=True)

        if errors:
            for error in errors:
                print(f"設定エラー: {error}")
            return False

        return True

    @classmethod
    def get_realtime_api_url(cls) -> str:
        """リアルタイムAPIのURLを取得"""
        return f"{cls.REALTIME_API_URL}?model={cls.OPENAI_MODEL}"

    @classmethod
    def print_config(cls):
        """現在の設定を表示（機密情報は隠す）"""
        print("=== アプリケーション設定 ===")
        print(f"プロジェクトルート: {cls.PROJECT_ROOT}")
        print(f"OpenAI Model: {cls.OPENAI_MODEL}")
        print(f"API Key: {'設定済み' if cls.OPENAI_API_KEY else '未設定'}")
        print(f"データベースパス: {cls.DATABASE_PATH}")
        print(f"ログファイル: {cls.LOG_FILE}")
        print(f"音声設定: {cls.AUDIO_SAMPLE_RATE}Hz, {cls.AUDIO_CHANNELS}ch")
        print(f"音声: {cls.REALTIME_VOICE}")
        print(f"Temperature: {cls.REALTIME_TEMPERATURE}")
        print()


# 設定の初期検証
if __name__ == "__main__":
    Config.print_config()
    if Config.validate_config():
        print("✅ 設定は正常です")
    else:
        print("❌ 設定に問題があります")