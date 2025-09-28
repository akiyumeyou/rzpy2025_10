#!/usr/bin/env python3
"""
リアルタイム音声会話エントリーポイント

OpenAI Realtime API を使用し、高齢者向けの音声会話を最小構成で実現する。
"""

import asyncio
import signal

from modules.config import Config
from modules.logger import get_logger
from modules.audio_handler import RealtimeAudioHandler


logger = get_logger(__name__)


class GracefulExit(RuntimeError):
    """Ctrl+C などで安全に終了するための例外"""


async def run_realtime_conversation():
    """Realtime API を用いた音声会話を実行"""
    if not Config.validate_config():
        raise GracefulExit("環境変数の設定を確認してください")

    handler = RealtimeAudioHandler()

    def handle_transcription(text: str):
        print(f"👂 ユーザー: {text}")

    def handle_error(error: str):
        print(f"⚠️ エラー: {error}")

    handler.set_callbacks(
        on_transcription=handle_transcription,
        on_error=handle_error,
    )

    if not await handler.start_realtime_session():
        raise GracefulExit("リアルタイムAPIセッションの開始に失敗しました")

    # 起動時の挨拶（必要に応じて省略可能）
    await handler.generate_initial_greeting()

    print("\n🎙️ リアルタイム会話を開始します。終了するには Ctrl+C を押してください。\n")

    try:
        await handler.stream_audio_conversation()
    finally:
        await handler.stop_conversation()


def main():
    """同期ラッパー"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    # Ctrl+C を GracefulExit にマップ
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, lambda: asyncio.ensure_future(cancel_tasks(loop)))

    try:
        loop.run_until_complete(run_realtime_conversation())
    except GracefulExit as exc:
        logger.error(str(exc))
    finally:
        cancel_pending = asyncio.all_tasks(loop)
        for task in cancel_pending:
            task.cancel()
        loop.run_until_complete(loop.shutdown_asyncgens())
        loop.close()


async def cancel_tasks(loop: asyncio.AbstractEventLoop):
    """全タスクをキャンセルし GracefulExit を発火"""
    tasks = [task for task in asyncio.all_tasks(loop) if not task.done()]
    for task in tasks:
        task.cancel()
    raise GracefulExit("ユーザー操作により終了しました")


if __name__ == "__main__":
    main()

