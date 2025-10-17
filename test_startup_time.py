#!/usr/bin/env python3
"""
起動時間の詳細分析スクリプト
"""
import time
import sys

def measure_time(description, func):
    """処理時間を計測"""
    start = time.time()
    result = func()
    elapsed = time.time() - start
    print(f"{description:40s}: {elapsed:6.3f}秒")
    return result, elapsed

print("=" * 70)
print("起動時間の詳細分析")
print("=" * 70)

total_start = time.time()

# 1. 標準ライブラリのインポート
def import_stdlib():
    import asyncio
    import os
    import signal
    import sys
    from datetime import datetime
    from typing import List
    return True

measure_time("1. 標準ライブラリ", import_stdlib)

# 2. 重いサードパーティライブラリ
def import_heavy_libs():
    import openai
    import gspread
    from google.oauth2.service_account import Credentials
    return True

measure_time("2. サードパーティライブラリ", import_heavy_libs)

# 3. configモジュール（.env読み込み含む）
def import_config():
    from modules.config import Config
    return True

measure_time("3. Config (.env読み込み)", import_config)

# 4. audio_handlerモジュール
def import_audio_handler():
    from modules.audio_handler import RealtimeAudioHandler
    return True

measure_time("4. audio_handler (PyAudio含む)", import_audio_handler)

# 5. その他のモジュール
def import_other_modules():
    from modules.logger import get_logger
    from modules.safety_checker import ConversationResult, SafetyStatus
    from modules.email_notifier import EmailNotifier
    return True

measure_time("5. その他のモジュール", import_other_modules)

# 6. emotion_analyzerモジュール（DB初期化含む）
def import_emotion_analyzer():
    from modules.emotion_analyzer import EmotionRecordManager
    return EmotionRecordManager()

emotion_manager, db_time = measure_time("6. emotion_analyzer (DB初期化)", import_emotion_analyzer)

# 7. google_sheetsモジュール（認証含む）
def import_google_sheets():
    from modules.google_sheets import GoogleSheetsManager
    return GoogleSheetsManager()

sheets_manager, sheets_time = measure_time("7. google_sheets (認証・初期化)", import_google_sheets)

# 8. RealtimeCareAppクラスのインスタンス化
def instantiate_app():
    from modules.config import Config
    from modules.audio_handler import RealtimeAudioHandler
    from modules.emotion_analyzer import EmotionRecordManager
    from modules.google_sheets import GoogleSheetsManager
    from modules.email_notifier import EmailNotifier

    # Config検証
    if not Config.validate_config():
        raise RuntimeError("環境変数の設定が不足しています")

    # 各マネージャーのインスタンス化
    handler = RealtimeAudioHandler()
    emotion_manager = EmotionRecordManager()
    google_sheets = GoogleSheetsManager()
    email_notifier = EmailNotifier()

    return True

measure_time("8. RealtimeCareApp初期化", instantiate_app)

total_elapsed = time.time() - total_start

print("=" * 70)
print(f"合計起動時間: {total_elapsed:.3f}秒")
print("=" * 70)
print()
print("【ボトルネック分析】")
print(f"- データベース初期化: {db_time:.3f}秒 ({db_time/total_elapsed*100:.1f}%)")
print(f"- Google Sheets初期化: {sheets_time:.3f}秒 ({sheets_time/total_elapsed*100:.1f}%)")
print()
