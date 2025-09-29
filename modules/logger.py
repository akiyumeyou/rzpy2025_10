"""
ログ管理モジュール
アプリケーション全体のログを統一管理
"""

import logging
import sys
from pathlib import Path
from typing import Optional

from .config import Config

# ログフォーマット
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def setup_logger(name: str, level: Optional[str] = None) -> logging.Logger:
    """ロガーのセットアップ"""
    logger = logging.getLogger(name)

    if logger.handlers:
        return logger

    log_level = level or Config.LOG_LEVEL
    logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    formatter = logging.Formatter(LOG_FORMAT, DATE_FORMAT)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    try:
        log_file_path = Path(Config.LOG_FILE)
        log_file_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(Config.LOG_FILE, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"ログファイルの設定に失敗しました: {exc}")

    logger.propagate = False
    return logger


def get_logger(name: str) -> logging.Logger:
    return setup_logger(name)


class AudioLogger:
    """音声処理専用のロガークラス"""

    def __init__(self, name: str = "audio"):
        self.logger = get_logger(name)

    def debug_audio(self, message: str, audio_data: Optional[bytes] = None):
        if audio_data:
            self.logger.debug(f"{message} (サイズ: {len(audio_data)} bytes)")
        else:
            self.logger.debug(message)

    def info_session(self, message: str):
        self.logger.info(f"[SESSION] {message}")

    def warning_connection(self, message: str):
        self.logger.warning(f"[CONNECTION] {message}")

    def error_api(self, message: str, error: Optional[Exception] = None):
        if error:
            self.logger.error(f"[API ERROR] {message}: {error}")
        else:
            self.logger.error(f"[API ERROR] {message}")


class ConversationLogger:
    """会話専用のロガークラス"""

    def __init__(self, name: str = "conversation"):
        self.logger = get_logger(name)

    def log_user_input(self, text: str):
        self.logger.info(f"[USER] {text}")

    def log_ai_response(self, text: str):
        self.logger.info(f"[AI] {text}")

    def log_transcription(self, text: str):
        self.logger.debug(f"[TRANSCRIPTION] {text}")

    def log_conversation_start(self, user_id: Optional[str] = None):
        user_info = f" (ユーザー: {user_id})" if user_id else ""
        self.logger.info(f"[CONVERSATION START]{user_info}")

    def log_conversation_end(self, duration: Optional[float] = None):
        duration_info = f" (時間: {duration:.1f}秒)" if duration else ""
        self.logger.info(f"[CONVERSATION END]{duration_info}")