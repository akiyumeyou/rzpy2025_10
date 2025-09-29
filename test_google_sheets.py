#!/usr/bin/env python3
"""
Googleシート連携テストスクリプト
設定が正しく行われているかを確認
"""

import os
import sys
from datetime import datetime

# モジュールパスを追加
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from modules.google_sheets import GoogleSheetsManager
from modules.safety_checker import ConversationResult, SafetyStatus

def test_configuration():
    """設定の確認"""
    print("🔧 Googleシート連携設定確認")
    print("="*50)

    # 環境変数確認
    spreadsheet_id = os.getenv('GOOGLE_SPREADSHEET_ID', '')
    credentials_path = os.path.join(os.path.dirname(__file__), 'credentials', 'google_service_account.json')

    print(f"📋 GOOGLE_SPREADSHEET_ID: {'✅ 設定済み' if spreadsheet_id else '❌ 未設定'}")
    print(f"🔑 認証ファイル: {'✅ 存在' if os.path.exists(credentials_path) else '❌ 不存在'}")

    if not spreadsheet_id:
        print("\n❌ GOOGLE_SPREADSHEET_IDが設定されていません")
        print("💡 .envファイルに以下を追加してください:")
        print("   GOOGLE_SPREADSHEET_ID=your_spreadsheet_id_here")
        return False

    if not os.path.exists(credentials_path):
        print(f"\n❌ 認証ファイルが見つかりません: {credentials_path}")
        print("💡 Google Cloud Consoleで作成したJSONファイルを配置してください")
        return False

    return True

def test_connection():
    """接続テスト"""
    print("\n🌐 Googleシート接続テスト")
    print("="*50)

    try:
        manager = GoogleSheetsManager()

        if not manager.is_available():
            print("❌ Googleシート機能が利用できません")
            return False

        print("✅ Googleシート接続成功")

        # スプレッドシート情報取得
        if manager.spreadsheet:
            print(f"📊 スプレッドシート名: {manager.spreadsheet.title}")
            print(f"🔗 URL: https://docs.google.com/spreadsheets/d/{manager.spreadsheet.id}")

        return True

    except Exception as e:
        print(f"❌ 接続エラー: {e}")
        return False

def test_record_writing():
    """テスト記録の書き込み"""
    print("\n✏️ テスト記録書き込み")
    print("="*50)

    try:
        manager = GoogleSheetsManager()

        if not manager.is_available():
            print("❌ Googleシート機能が利用できません")
            return False

        # テストデータ作成
        test_result = ConversationResult(
            timestamp=datetime.now().isoformat(),
            duration=120.5,
            user_responses=["今日は元気です", "薬も飲んでいます", "散歩もしました"],
            ai_responses=["それは良かったです", "お薬もちゃんと飲んで偉いですね", "散歩は大切ですね"],
            safety_status=SafetyStatus.SAFE,
            emotion_score=0.8,
            keywords=["元気", "薬", "散歩"],
            summary="体調良好、日常生活順調",
            needs_followup=False
        )

        # 記録保存
        success = manager.record_conversation(test_result, "テストユーザー")

        if success:
            print("✅ テスト記録の保存に成功しました")
            print("📊 Googleシートを確認してください")
            return True
        else:
            print("❌ テスト記録の保存に失敗しました")
            return False

    except Exception as e:
        print(f"❌ 書き込みエラー: {e}")
        return False

def test_reading():
    """記録読み取りテスト"""
    print("\n📖 記録読み取りテスト")
    print("="*50)

    try:
        manager = GoogleSheetsManager()

        if not manager.is_available():
            print("❌ Googleシート機能が利用できません")
            return False

        # 最近の記録取得
        records = manager.get_recent_records(7)
        print(f"📋 過去7日間の記録: {len(records)}件")

        # サマリーレポート生成
        summary = manager.generate_summary_report(7)
        if summary:
            print("\n📊 サマリーレポート:")
            print(summary)

        return True

    except Exception as e:
        print(f"❌ 読み取りエラー: {e}")
        return False

def main():
    """メイン実行"""
    print("🧪 Googleシート連携 総合テスト")
    print("="*60)

    # 設定確認
    if not test_configuration():
        print("\n❌ 設定が不完全です。上記の指示に従って設定を完了してください。")
        return

    # 接続テスト
    if not test_connection():
        print("\n❌ 接続に失敗しました。設定を確認してください。")
        return

    # 書き込みテスト
    if not test_record_writing():
        print("\n❌ 書き込みに失敗しました。")
        return

    # 読み取りテスト
    if not test_reading():
        print("\n❌ 読み取りに失敗しました。")
        return

    print("\n🎉 全てのテストが成功しました！")
    print("✅ Googleシート連携が正常に動作しています")
    print("\n💡 次のステップ:")
    print("   1. main.py でリアルタイム会話をテスト")
    print("   2. 会話終了後にGoogleシートを確認")
    print("   3. メール通知設定（必要に応じて）")

if __name__ == "__main__":
    main()