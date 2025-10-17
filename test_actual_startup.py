#!/usr/bin/env python3
"""
実際のmain.py起動時間を計測
"""
import time
import sys

print("=" * 70)
print("main.py 起動時間計測")
print("=" * 70)

start = time.time()

# main.pyのインポート
from main import RealtimeCareApp

import_time = time.time() - start
print(f"インポート完了: {import_time:.3f}秒")

# RealtimeCareAppのインスタンス化
inst_start = time.time()
try:
    app = RealtimeCareApp()
    inst_time = time.time() - inst_start
    print(f"インスタンス化完了: {inst_time:.3f}秒")
except Exception as e:
    inst_time = time.time() - inst_start
    print(f"インスタンス化エラー: {inst_time:.3f}秒 - {e}")

total_time = time.time() - start

print("=" * 70)
print(f"合計起動時間: {total_time:.3f}秒")
print("=" * 70)
