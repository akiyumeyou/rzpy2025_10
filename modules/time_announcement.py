"""
時報機能モジュール
1日1回の会話開始合図として現在時刻を音声でお知らせ
"""

import datetime
import asyncio
from typing import Optional

class TimeAnnouncement:
    def __init__(self):
        self.announcement_made = False

    def get_time_message(self) -> str:
        """時報メッセージを生成"""
        now = datetime.datetime.now()
        hour = now.hour
        minute = now.minute

        # 時間帯に応じた挨拶
        if 5 <= hour < 12:
            greeting = "おはようございます"
        elif 12 <= hour < 17:
            greeting = "こんにちは"
        else:
            greeting = "こんばんは"

        message = f"{greeting}。現在の時刻は{hour}時{minute}分です。今日もお話ししましょう。"
        return message

    async def announce_time(self) -> str:
        """時報を実行"""
        if self.announcement_made:
            print("⏰ 本日の時報は既に実行済みです")
            return None

        message = self.get_time_message()
        print(f"⏰ 時報: {message}")

        # 時報完了フラグ
        self.announcement_made = True

        return message

    def reset_announcement(self):
        """時報フラグをリセット（テスト用）"""
        self.announcement_made = False

async def test_time_announcement():
    """時報機能テスト"""
    announcer = TimeAnnouncement()

    print("=== 時報機能テスト ===")
    await announcer.announce_time()

    # 重複実行テスト
    print("\n=== 重複実行テスト ===")
    await announcer.announce_time()

    # リセットテスト
    print("\n=== リセット後再実行テスト ===")
    announcer.reset_announcement()
    await announcer.announce_time()

if __name__ == "__main__":
    asyncio.run(test_time_announcement())