"""
スケジューラーと時報機能
定時の安否確認と時間管理
"""

import asyncio
import schedule
import time
from datetime import datetime, timedelta
from typing import List, Callable, Optional, Dict
from dataclasses import dataclass
from threading import Thread
import threading

from .config import Config
from .logger import get_logger
from .safety_checker import SafetyChecker, ConversationResult

logger = get_logger(__name__)

@dataclass
class ScheduledCheck:
    """スケジュールされた安否確認"""
    time: str  # "10:00" format
    user_name: str
    enabled: bool = True
    last_executed: Optional[str] = None

class TimeAnnouncementScheduler:
    """時報・スケジューラー"""

    def __init__(self):
        self.scheduled_checks: List[ScheduledCheck] = []
        self.running = False
        self.scheduler_thread: Optional[Thread] = None

        # コールバック
        self.on_scheduled_check: Optional[Callable[[str, str], None]] = None
        self.on_time_announcement: Optional[Callable[[str], None]] = None

        # デフォルトスケジュール設定
        self._setup_default_schedule()

    def _setup_default_schedule(self):
        """デフォルトのスケジュール設定"""
        default_times = Config.SAFETY_CHECK_TIMES
        default_user = "田中さん"  # 設定から取得予定

        for check_time in default_times:
            self.add_scheduled_check(check_time, default_user)

        logger.info(f"デフォルトスケジュール設定完了: {len(default_times)}件")

    def add_scheduled_check(self, time_str: str, user_name: str) -> bool:
        """スケジュールに安否確認を追加"""
        try:
            # 時刻形式の検証
            datetime.strptime(time_str, "%H:%M")

            scheduled_check = ScheduledCheck(
                time=time_str,
                user_name=user_name
            )

            self.scheduled_checks.append(scheduled_check)

            # scheduleライブラリに登録
            schedule.every().day.at(time_str).do(
                self._execute_scheduled_check,
                time_str,
                user_name
            )

            logger.info(f"安否確認スケジュール追加: {time_str} - {user_name}")
            return True

        except ValueError as e:
            logger.error(f"無効な時刻形式: {time_str} - {e}")
            return False

    def remove_scheduled_check(self, time_str: str, user_name: str) -> bool:
        """スケジュールから安否確認を削除"""
        self.scheduled_checks = [
            check for check in self.scheduled_checks
            if not (check.time == time_str and check.user_name == user_name)
        ]

        # scheduleライブラリからも削除（再設定）
        schedule.clear()
        for check in self.scheduled_checks:
            if check.enabled:
                schedule.every().day.at(check.time).do(
                    self._execute_scheduled_check,
                    check.time,
                    check.user_name
                )

        logger.info(f"安否確認スケジュール削除: {time_str} - {user_name}")
        return True

    def enable_schedule(self, time_str: str, user_name: str):
        """スケジュールを有効化"""
        for check in self.scheduled_checks:
            if check.time == time_str and check.user_name == user_name:
                check.enabled = True
                break

    def disable_schedule(self, time_str: str, user_name: str):
        """スケジュールを無効化"""
        for check in self.scheduled_checks:
            if check.time == time_str and check.user_name == user_name:
                check.enabled = False
                break

    def _execute_scheduled_check(self, time_str: str, user_name: str):
        """スケジュールされた安否確認を実行"""
        logger.info(f"定時安否確認開始: {time_str} - {user_name}")

        # 時報アナウンス
        self._announce_time(time_str)

        # 安否確認実行のコールバック
        if self.on_scheduled_check:
            self.on_scheduled_check(time_str, user_name)

        # 実行時刻を記録
        for check in self.scheduled_checks:
            if check.time == time_str and check.user_name == user_name:
                check.last_executed = datetime.now().isoformat()
                break

    def _announce_time(self, time_str: str):
        """時報をアナウンス"""
        hour, minute = time_str.split(":")

        if minute == "00":
            announcement = f"{int(hour)}時になりました。"
        else:
            announcement = f"{int(hour)}時{int(minute)}分になりました。"

        logger.info(f"時報: {announcement}")

        if self.on_time_announcement:
            self.on_time_announcement(announcement)

    def start(self):
        """スケジューラーを開始"""
        if self.running:
            logger.warning("スケジューラーは既に実行中です")
            return

        self.running = True
        self.scheduler_thread = Thread(target=self._run_scheduler, daemon=True)
        self.scheduler_thread.start()

        logger.info("スケジューラー開始")

    def stop(self):
        """スケジューラーを停止"""
        self.running = False
        if self.scheduler_thread:
            self.scheduler_thread.join(timeout=1)

        logger.info("スケジューラー停止")

    def _run_scheduler(self):
        """スケジューラーのメインループ"""
        while self.running:
            schedule.run_pending()
            time.sleep(1)

    def get_next_scheduled_time(self) -> Optional[str]:
        """次回の安否確認時刻を取得"""
        now = datetime.now()
        today_checks = []

        for check in self.scheduled_checks:
            if not check.enabled:
                continue

            check_time = datetime.strptime(check.time, "%H:%M").time()
            check_datetime = datetime.combine(now.date(), check_time)

            if check_datetime > now:
                today_checks.append(check_datetime)

        if today_checks:
            next_check = min(today_checks)
            return next_check.strftime("%H:%M")

        # 今日に予定がない場合は明日の最初
        tomorrow_checks = [
            datetime.strptime(check.time, "%H:%M").time()
            for check in self.scheduled_checks
            if check.enabled
        ]

        if tomorrow_checks:
            earliest = min(tomorrow_checks)
            return earliest.strftime("%H:%M")

        return None

    def get_schedule_status(self) -> Dict:
        """スケジュール状況を取得"""
        return {
            "running": self.running,
            "scheduled_checks": [
                {
                    "time": check.time,
                    "user_name": check.user_name,
                    "enabled": check.enabled,
                    "last_executed": check.last_executed
                }
                for check in self.scheduled_checks
            ],
            "next_check": self.get_next_scheduled_time()
        }

    def set_callbacks(self,
                     on_scheduled_check: Optional[Callable[[str, str], None]] = None,
                     on_time_announcement: Optional[Callable[[str], None]] = None):
        """コールバック関数を設定"""
        if on_scheduled_check:
            self.on_scheduled_check = on_scheduled_check
        if on_time_announcement:
            self.on_time_announcement = on_time_announcement


class SafetyCheckManager:
    """安否確認マネージャー（スケジューラー統合版）"""

    def __init__(self):
        self.scheduler = TimeAnnouncementScheduler()
        self.active_checks: Dict[str, SafetyChecker] = {}

        # スケジューラーのコールバック設定
        self.scheduler.set_callbacks(
            on_scheduled_check=self._handle_scheduled_check,
            on_time_announcement=self._handle_time_announcement
        )

        self.on_check_complete: Optional[Callable[[str, ConversationResult], None]] = None

    async def _handle_scheduled_check(self, time_str: str, user_name: str):
        """スケジュールされた安否確認の処理"""
        check_id = f"{user_name}_{time_str}"

        if check_id in self.active_checks:
            logger.warning(f"安否確認が既に実行中: {check_id}")
            return

        try:
            # 安否確認実行
            checker = SafetyChecker(user_name)
            self.active_checks[check_id] = checker

            # 安否確認実行
            result = await checker.start_safety_check()

            # 結果の処理
            logger.info(f"安否確認完了: {user_name} - {result.safety_status.value}")

            if self.on_check_complete:
                self.on_check_complete(user_name, result)

        except Exception as e:
            logger.error(f"安否確認エラー: {check_id} - {e}")
        finally:
            # クリーンアップ
            if check_id in self.active_checks:
                del self.active_checks[check_id]

    def _handle_time_announcement(self, announcement: str):
        """時報の処理"""
        logger.info(f"時報アナウンス: {announcement}")
        # 実際の音声出力や通知は別途実装

    def start_manager(self):
        """マネージャーを開始"""
        self.scheduler.start()
        logger.info("安否確認マネージャー開始")

    def stop_manager(self):
        """マネージャーを停止"""
        self.scheduler.stop()
        logger.info("安否確認マネージャー停止")

    def add_user_schedule(self, user_name: str, times: List[str]) -> bool:
        """ユーザーのスケジュールを追加"""
        success = True
        for time_str in times:
            if not self.scheduler.add_scheduled_check(time_str, user_name):
                success = False

        return success

    def get_status(self) -> Dict:
        """システム状況を取得"""
        return {
            "scheduler": self.scheduler.get_schedule_status(),
            "active_checks": list(self.active_checks.keys())
        }

    def set_completion_callback(self, callback: Callable[[str, ConversationResult], None]):
        """完了コールバックを設定"""
        self.on_check_complete = callback


# 使用例
async def example_scheduler():
    """スケジューラーの使用例"""
    manager = SafetyCheckManager()

    def on_check_complete(user_name: str, result: ConversationResult):
        print(f"✅ {user_name}の安否確認完了")
        print(f"   ステータス: {result.safety_status.value}")
        print(f"   感情スコア: {result.emotion_score:.2f}")

        if result.needs_followup:
            print("   ⚠️ フォローアップが必要です")

    manager.set_completion_callback(on_check_complete)

    # マネージャー開始
    manager.start_manager()

    # ステータス確認
    print("スケジュール状況:")
    status = manager.get_status()
    print(status)

    try:
        # 無限ループで実行
        while True:
            await asyncio.sleep(60)
    except KeyboardInterrupt:
        print("終了します...")
        manager.stop_manager()


if __name__ == "__main__":
    asyncio.run(example_scheduler())