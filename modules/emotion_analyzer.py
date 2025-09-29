"""
感情分析・記録機能
会話内容の感情分析とデータベース記録
"""

import sqlite3
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import os

from .config import Config
from .logger import get_logger
from .safety_checker import ConversationResult, SafetyStatus

logger = get_logger(__name__)

class EmotionCategory(Enum):
    """感情カテゴリ"""
    POSITIVE = "positive"      # ポジティブ
    NEUTRAL = "neutral"        # 中立
    NEGATIVE = "negative"      # ネガティブ
    ANXIOUS = "anxious"        # 不安
    DEPRESSED = "depressed"    # 憂鬱
    ENERGETIC = "energetic"    # 元気

@dataclass
class EmotionAnalysis:
    """感情分析結果"""
    timestamp: str
    overall_score: float           # -1.0 to 1.0
    category: EmotionCategory
    confidence: float              # 0.0 to 1.0
    detected_keywords: List[str]
    sentiment_details: Dict[str, float]
    health_indicators: Dict[str, bool]

@dataclass
class ConversationRecord:
    """会話記録"""
    id: Optional[int]
    timestamp: str
    duration: float
    safety_status: str
    emotion_score: float
    emotion_category: str
    user_responses: str            # JSON string
    ai_responses: str              # JSON string
    summary: str
    needs_followup: bool
    follow_up_completed: bool = False

class EmotionAnalyzer:
    """感情分析器"""

    def __init__(self):
        # 感情辞書
        self.emotion_keywords = {
            EmotionCategory.POSITIVE: [
                "元気", "良い", "大丈夫", "楽しい", "嬉しい", "ありがとう",
                "健康", "調子良い", "気分良い", "満足", "幸せ", "安心"
            ],
            EmotionCategory.NEGATIVE: [
                "痛い", "悪い", "しんどい", "疲れた", "つらい", "困った",
                "調子悪い", "気分悪い", "苦しい", "嫌", "だめ"
            ],
            EmotionCategory.ANXIOUS: [
                "心配", "不安", "怖い", "緊張", "落ち着かない", "ドキドキ",
                "気になる", "心配性", "不安定"
            ],
            EmotionCategory.DEPRESSED: [
                "寂しい", "悲しい", "むなしい", "落ち込む", "憂鬱", "やる気ない",
                "つまらない", "絶望", "暗い"
            ],
            EmotionCategory.ENERGETIC: [
                "元気", "活発", "やる気", "パワフル", "積極的", "前向き",
                "頑張る", "張り切る", "活動的"
            ]
        }

        # 健康指標キーワード
        self.health_keywords = {
            "pain": ["痛い", "痛み", "ひりひり", "ずきずき", "チクチク"],
            "fatigue": ["疲れた", "だるい", "しんどい", "疲労"],
            "sleep": ["眠れない", "不眠", "寝不足", "睡眠", "よく眠れた"],
            "appetite": ["食欲ない", "食べられない", "おいしい", "食欲"],
            "mobility": ["歩けない", "動けない", "転んだ", "よく歩いた"],
            "medication": ["薬", "服薬", "飲み忘れ", "薬を飲んだ"]
        }

    def analyze_emotion(self, user_responses: List[str]) -> EmotionAnalysis:
        """感情分析を実行"""
        if not user_responses:
            return self._create_neutral_analysis()

        all_text = " ".join(user_responses)

        # 各カテゴリのスコア計算
        category_scores = {}
        detected_keywords = []

        for category, keywords in self.emotion_keywords.items():
            score = 0
            for keyword in keywords:
                if keyword in all_text:
                    score += 1
                    detected_keywords.append(keyword)

            # 正規化（全体の単語数に対する割合）
            total_words = len(all_text.split())
            normalized_score = score / max(total_words * 0.1, 1)
            category_scores[category.value] = normalized_score

        # 全体的な感情スコア計算
        overall_score = self._calculate_overall_score(category_scores)

        # 主要カテゴリの決定
        primary_category = self._determine_primary_category(category_scores)

        # 信頼度計算
        confidence = self._calculate_confidence(category_scores, detected_keywords)

        # 健康指標の分析
        health_indicators = self._analyze_health_indicators(all_text)

        return EmotionAnalysis(
            timestamp=datetime.now().isoformat(),
            overall_score=overall_score,
            category=primary_category,
            confidence=confidence,
            detected_keywords=detected_keywords,
            sentiment_details=category_scores,
            health_indicators=health_indicators
        )

    def _calculate_overall_score(self, category_scores: Dict[str, float]) -> float:
        """全体的な感情スコアを計算"""
        positive_score = category_scores.get(EmotionCategory.POSITIVE.value, 0)
        energetic_score = category_scores.get(EmotionCategory.ENERGETIC.value, 0)
        negative_score = category_scores.get(EmotionCategory.NEGATIVE.value, 0)
        anxious_score = category_scores.get(EmotionCategory.ANXIOUS.value, 0)
        depressed_score = category_scores.get(EmotionCategory.DEPRESSED.value, 0)

        positive_total = positive_score + energetic_score
        negative_total = negative_score + anxious_score + depressed_score

        # -1.0 to 1.0 の範囲に正規化
        score = positive_total - negative_total
        return max(-1.0, min(1.0, score))

    def _determine_primary_category(self, category_scores: Dict[str, float]) -> EmotionCategory:
        """主要な感情カテゴリを決定"""
        if not category_scores:
            return EmotionCategory.NEUTRAL

        max_category = max(category_scores.items(), key=lambda x: x[1])

        if max_category[1] < 0.1:  # 閾値以下の場合は中立
            return EmotionCategory.NEUTRAL

        return EmotionCategory(max_category[0])

    def _calculate_confidence(self, category_scores: Dict[str, float], keywords: List[str]) -> float:
        """信頼度を計算"""
        if not keywords:
            return 0.0

        # キーワード数と最高スコアから信頼度を計算
        max_score = max(category_scores.values()) if category_scores else 0
        keyword_factor = min(len(keywords) * 0.2, 1.0)

        return min(max_score + keyword_factor, 1.0)

    def _analyze_health_indicators(self, text: str) -> Dict[str, bool]:
        """健康指標を分析"""
        indicators = {}

        for indicator, keywords in self.health_keywords.items():
            indicators[indicator] = any(keyword in text for keyword in keywords)

        return indicators

    def _create_neutral_analysis(self) -> EmotionAnalysis:
        """中立的な分析結果を作成"""
        return EmotionAnalysis(
            timestamp=datetime.now().isoformat(),
            overall_score=0.0,
            category=EmotionCategory.NEUTRAL,
            confidence=0.0,
            detected_keywords=[],
            sentiment_details={},
            health_indicators={}
        )


class ConversationDatabase:
    """会話記録データベース"""

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or Config.DATABASE_PATH
        self._initialize_database()

    def _initialize_database(self):
        """データベースの初期化"""
        try:
            # データベースディレクトリの作成
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

            with sqlite3.connect(self.db_path) as conn:
                # 既存テーブルを一度削除して新スキーマを適用
                conn.execute("DROP TABLE IF EXISTS emotion_analysis")
                conn.execute("DROP TABLE IF EXISTS conversations")

                conn.execute("""
                    CREATE TABLE IF NOT EXISTS conversations (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT NOT NULL,
                        duration REAL NOT NULL,
                        safety_status TEXT NOT NULL,
                        emotion_score REAL NOT NULL,
                        emotion_category TEXT NOT NULL,
                        user_responses TEXT NOT NULL,
                        ai_responses TEXT NOT NULL,
                        summary TEXT NOT NULL,
                        needs_followup BOOLEAN NOT NULL,
                        follow_up_completed BOOLEAN DEFAULT FALSE,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)

                conn.execute("""
                    CREATE TABLE IF NOT EXISTS emotion_analysis (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        conversation_id INTEGER,
                        timestamp TEXT NOT NULL,
                        overall_score REAL NOT NULL,
                        category TEXT NOT NULL,
                        confidence REAL NOT NULL,
                        detected_keywords TEXT NOT NULL,
                        sentiment_details TEXT NOT NULL,
                        health_indicators TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (conversation_id) REFERENCES conversations (id)
                    )
                """)

                conn.commit()
                logger.info(f"データベース初期化完了: {self.db_path}")

        except Exception as e:
            logger.error(f"データベース初期化エラー: {e}")
            raise

    def save_conversation(self, result: ConversationResult, emotion_analysis: EmotionAnalysis) -> int:
        """会話記録を保存"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # 会話記録の保存
                cursor = conn.execute("""
                    INSERT INTO conversations (
                        timestamp, duration, safety_status, emotion_score,
                        emotion_category, user_responses, ai_responses,
                        summary, needs_followup
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    result.timestamp,
                    result.duration,
                    result.safety_status.value,
                    result.emotion_score,
                    emotion_analysis.category.value,
                    json.dumps(result.user_responses, ensure_ascii=False),
                    json.dumps(result.ai_responses, ensure_ascii=False),
                    result.summary,
                    int(result.needs_followup)
                ))

                conversation_id = cursor.lastrowid

                # 感情分析の保存
                conn.execute("""
                    INSERT INTO emotion_analysis (
                        conversation_id, timestamp, overall_score, category,
                        confidence, detected_keywords, sentiment_details, health_indicators
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    conversation_id,
                    emotion_analysis.timestamp,
                    emotion_analysis.overall_score,
                    emotion_analysis.category.value,
                    emotion_analysis.confidence,
                    json.dumps(emotion_analysis.detected_keywords, ensure_ascii=False),
                    json.dumps(emotion_analysis.sentiment_details, ensure_ascii=False),
                    json.dumps(emotion_analysis.health_indicators, ensure_ascii=False)
                ))

                conn.commit()
                logger.info(f"会話記録保存完了: ID={conversation_id}")
                return conversation_id

        except Exception as e:
            logger.error(f"会話記録保存エラー: {e}")
            raise

    def get_recent_conversations(self, days: int = 7) -> List[ConversationRecord]:
        """最近の会話記録を取得"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row

                since_date = datetime.now() - timedelta(days=days)

                cursor = conn.execute("""
                    SELECT * FROM conversations
                    WHERE timestamp >= ?
                    ORDER BY timestamp DESC
                """, (since_date.isoformat(),))

                records = []
                for row in cursor:
                    records.append(
                        ConversationRecord(
                            id=row['id'],
                            timestamp=row['timestamp'],
                            duration=row['duration'],
                            safety_status=row['safety_status'],
                            emotion_score=row['emotion_score'],
                            emotion_category=row['emotion_category'],
                            user_responses=row['user_responses'],
                            ai_responses=row['ai_responses'],
                        summary=row['summary'],
                        needs_followup=bool(row['needs_followup']),
                        follow_up_completed=bool(row['follow_up_completed'])
                        )
                    )

                return records

        except Exception as e:
            logger.error(f"会話記録取得エラー: {e}")
            return []

    def get_emotion_trends(self, days: int = 30) -> Dict:
        """感情の傾向を分析"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                since_date = datetime.now() - timedelta(days=days)

                # 感情スコアの推移
                cursor = conn.execute("""
                    SELECT DATE(timestamp) as date, AVG(emotion_score) as avg_score
                    FROM conversations
                    WHERE timestamp >= ?
                    GROUP BY DATE(timestamp)
                    ORDER BY date
                """, (since_date.isoformat(),))

                emotion_trends = [{"date": row[0], "score": row[1]} for row in cursor]

                # カテゴリ別集計
                cursor = conn.execute("""
                    SELECT emotion_category, COUNT(*) as count
                    FROM conversations
                    WHERE timestamp >= ?
                    GROUP BY emotion_category
                """, (since_date.isoformat(),))

                category_counts = {row[0]: row[1] for row in cursor}

                return {
                    "emotion_trends": emotion_trends,
                    "category_distribution": category_counts,
                    "period_days": days
                }

        except Exception as e:
            logger.error(f"感情傾向分析エラー: {e}")
            return {}

    def mark_followup_completed(self, conversation_id: int):
        """フォローアップ完了をマーク"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    UPDATE conversations
                    SET follow_up_completed = TRUE
                    WHERE id = ?
                """, (conversation_id,))
                conn.commit()

                logger.info(f"フォローアップ完了マーク: ID={conversation_id}")

        except Exception as e:
            logger.error(f"フォローアップ更新エラー: {e}")


class EmotionRecordManager:
    """感情分析・記録統合マネージャー"""

    def __init__(self):
        self.analyzer = EmotionAnalyzer()
        self.database = ConversationDatabase()

    def process_conversation(self, result: ConversationResult) -> Tuple[EmotionAnalysis, int]:
        """会話結果を処理（分析 + 記録）"""
        # 感情分析
        emotion_analysis = self.analyzer.analyze_emotion(result.user_responses)

        # データベース保存
        conversation_id = self.database.save_conversation(result, emotion_analysis)

        logger.info(f"会話処理完了: {emotion_analysis.category.value} (スコア: {emotion_analysis.overall_score:.2f})")

        return emotion_analysis, conversation_id

    def get_health_summary(self, days: int = 7) -> Dict:
        """健康状況の要約を取得"""
        conversations = self.database.get_recent_conversations(days)
        trends = self.database.get_emotion_trends(days)

        # 安否確認の統計
        safety_stats = {}
        total_conversations = len(conversations)

        if total_conversations > 0:
            for conv in conversations:
                status = conv.safety_status
                safety_stats[status] = safety_stats.get(status, 0) + 1

            # パーセンテージに変換
            safety_stats = {k: (v / total_conversations) * 100 for k, v in safety_stats.items()}

        return {
            "period_days": days,
            "total_conversations": total_conversations,
            "safety_statistics": safety_stats,
            "emotion_trends": trends,
            "needs_attention": sum(1 for conv in conversations if conv.needs_followup and not conv.follow_up_completed)
        }


# 使用例
def example_emotion_analysis():
    """感情分析の使用例"""
    manager = EmotionRecordManager()

    # テスト用の会話結果
    from .safety_checker import ConversationResult, SafetyStatus

    test_result = ConversationResult(
        timestamp=datetime.now().isoformat(),
        duration=120.5,
        user_responses=["元気です", "薬は飲んでいます", "少し疲れました"],
        ai_responses=["こんにちは", "お薬について", "お疲れ様です"],
        safety_status=SafetyStatus.SAFE,
        emotion_score=0.3,
        keywords=["元気", "薬", "疲れ"],
        summary="全体的に良好",
        needs_followup=False
    )

    # 処理実行
    emotion_analysis, conv_id = manager.process_conversation(test_result)
    print(f"感情分析結果: {emotion_analysis.category.value}")
    print(f"信頼度: {emotion_analysis.confidence:.2f}")

    # 健康要約
    health_summary = manager.get_health_summary()
    print(f"健康要約: {health_summary}")


if __name__ == "__main__":
    example_emotion_analysis()