"""TG PRO QUANTUM - AI Customer Service Engine"""
import re
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from .utils import DATA_DIR, log, log_error

CS_CONFIG_FILE = DATA_DIR / "cs_config.json"
KNOWLEDGE_BASE_FILE = DATA_DIR / "knowledge_base.json"

class Intent(Enum):
    GREETING = "greeting"
    QUESTION = "question"
    COMPLAINT = "complaint"
    COMPLIMENT = "compliment"
    ORDER = "order"
    SUPPORT = "support"
    FAREWELL = "farewell"
    UNKNOWN = "unknown"

class Sentiment(Enum):
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"

@dataclass
class ConversationContext:
    user_id: str
    account_id: str
    intent: Intent = Intent.UNKNOWN
    sentiment: Sentiment = Sentiment.NEUTRAL
    last_message: Optional[str] = None
    message_count: int = 0
    started_at: str = field(default_factory=lambda: datetime.now().isoformat())
    last_activity: str = field(default_factory=lambda: datetime.now().isoformat())

@dataclass
class ResponseTemplate:
    intent: Intent
    patterns: List[str]
    responses: List[str]
    priority: int = 1

    def matches(self, message: str) -> bool:
        message_lower = message.lower()
        for pattern in self.patterns:
            if pattern.lower() in message_lower: return True
        return False

    def get_response(self) -> str:
        import random
        return random.choice(self.responses)

class NLPProcessor:
    INTENT_KEYWORDS = {
        Intent.GREETING: ["hi", "hello", "hey", "halo", "pagi", "siang", "malam"],
        Intent.QUESTION: ["?", "what", "how", "when", "where", "why", "apa", "bagaimana", "kapan"],
        Intent.COMPLAINT: ["complaint", "problem", "issue", "error", "not working", "komplain", "masalah"],
        Intent.COMPLIMENT: ["good", "great", "excellent", "thanks", "terima kasih", "mantap", "keren"],
        Intent.ORDER: ["order", "buy", "purchase", "price", "cost", "beli", "harga", "pesan"],
        Intent.SUPPORT: ["help", "support", "assist", "bantuan", "tolong"],
        Intent.FAREWELL: ["bye", "goodbye", "see you", "dadah", "sampai jumpa"],
    }
    POSITIVE_WORDS = ["good", "great", "excellent", "love", "happy", "thank", "mantap", "keren", "bagus"]
    NEGATIVE_WORDS = ["bad", "terrible", "hate", "angry", "problem", "error", "issue", "buruk", "jelek", "marah"]

    @classmethod
    def detect_intent(cls, message: str) -> Intent:
        message_lower = message.lower()
        scores = {}
        for intent, keywords in cls.INTENT_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw.lower() in message_lower)
            if score > 0: scores[intent] = score
        if scores: return max(scores, key=scores.get)
        if "?" in message: return Intent.QUESTION
        return Intent.UNKNOWN

    @classmethod
    def detect_sentiment(cls, message: str) -> Sentiment:
        message_lower = message.lower()
        positive_count = sum(1 for word in cls.POSITIVE_WORDS if word in message_lower)
        negative_count = sum(1 for word in cls.NEGATIVE_WORDS if word in message_lower)
        if positive_count > negative_count + 1: return Sentiment.POSITIVE
        elif negative_count > positive_count + 1: return Sentiment.NEGATIVE
        return Sentiment.NEUTRAL

class AICSEngine:
    def __init__(self, api_key: Optional[str] = None):
        self.config_file = CS_CONFIG_FILE
        self.kb_file = KNOWLEDGE_BASE_FILE
        self.api_key = api_key
        self.config = self._load_config()
        self.knowledge_base = self._load_knowledge_base()
        self.templates = self._init_templates()
        self.conversations: Dict[str, ConversationContext] = {}

    def _load_config(self) -> Dict:
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f: return json.load(f)
            except: pass
        return {"enabled": True, "auto_reply": True, "escalation_threshold": 3, "response_delay_min": 2, "response_delay_max": 8}

    def _load_knowledge_base(self) -> Dict:
        if self.kb_file.exists():
            try:
                with open(self.kb_file, 'r', encoding='utf-8') as f: return json.load(f)
            except: pass
        return {"questions": [{"question": "berapa harga", "answer": "Silakan cek katalog terbaru"}, {"question": "cara order", "answer": "Klik link untuk order"}]}

    def _init_templates(self) -> List[ResponseTemplate]:
        return [
            ResponseTemplate(intent=Intent.GREETING, patterns=["hi", "hello", "hey", "halo", "pagi"], responses=["Halo! 👋 Ada yang bisa saya bantu?", "Hi! Selamat datang! 😊"], priority=10),
            ResponseTemplate(intent=Intent.QUESTION, patterns=["?", "apa", "bagaimana", "kapan", "berapa"], responses=["Pertanyaan yang bagus! Mari saya bantu jawab. 🤔"], priority=5),
            ResponseTemplate(intent=Intent.COMPLAINT, patterns=["komplain", "masalah", "error", "tidak bisa"], responses=["Mohon maaf atas ketidaknyamanan ini. 🙏 Bisa dijelaskan lebih detail?"], priority=15),
            ResponseTemplate(intent=Intent.COMPLIMENT, patterns=["terima kasih", "mantap", "keren", "bagus"], responses=["Sama-sama! 😊 Senang bisa membantu!"], priority=8),
            ResponseTemplate(intent=Intent.FAREWELL, patterns=["bye", "dadah", "sampai jumpa"], responses=["Sampai jumpa! 👋 Semoga harimu menyenangkan!"], priority=3),
            ResponseTemplate(intent=Intent.UNKNOWN, patterns=[], responses=["Maaf, saya belum mengerti. Bisa diulang?", "Mohon maaf, saya masih belajar. 📚"], priority=1),
        ]

    async def process_message(self, account_id: str, user_id: str, message: str) -> Dict:
        if not self.config.get("enabled", True): return {"responded": False, "reason": "CS disabled"}
        conv_key = f"{account_id}:{user_id}"
        if conv_key not in self.conversations:
            self.conversations[conv_key] = ConversationContext(user_id=user_id, account_id=account_id)
        context = self.conversations[conv_key]
        context.last_message = message
        context.message_count += 1
        context.last_activity = datetime.now().isoformat()
        intent = NLPProcessor.detect_intent(message)
        sentiment = NLPProcessor.detect_sentiment(message)
        context.intent = intent
        context.sentiment = sentiment
        kb_response = self._search_knowledge_base(message)
        if kb_response:
            response = kb_response
            source = "knowledge_base"
        else:
            template = self._find_best_template(message, intent)
            response = template.get_response()
            source = "template"
        response = self._personalize_response(response, context)
        return {"responded": True, "response": response, "intent": intent.value, "sentiment": sentiment.value, "source": source, "conversation_count": context.message_count}

    def _find_best_template(self, message: str, intent: Intent) -> ResponseTemplate:
        sorted_templates = sorted(self.templates, key=lambda t: t.priority, reverse=True)
        for template in sorted_templates:
            if template.matches(message): return template
        return next(t for t in self.templates if t.intent == Intent.UNKNOWN)

    def _search_knowledge_base(self, message: str) -> Optional[str]:
        message_lower = message.lower()
        for qa in self.knowledge_base.get("questions", []):
            question = qa.get("question", "").lower()
            if any(kw in message_lower for kw in question.split() if len(kw) > 3):
                return qa.get("answer", "")
        return None

    def _personalize_response(self, response: str, context: ConversationContext) -> str:
        return response.replace("{user}", context.user_id).replace("{time}", datetime.now().strftime("%H:%M"))

    def add_knowledge(self, question: str, answer: str) -> bool:
        self.knowledge_base.setdefault("questions", []).append({"question": question, "answer": answer, "added_at": datetime.now().isoformat()})
        self._save_knowledge_base()
        log(f"Added to knowledge base: {question[:50]}...", "success")
        return True

    def _save_knowledge_base(self):
        try:
            self.kb_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.kb_file, 'w', encoding='utf-8') as f: json.dump(self.knowledge_base, f, indent=2)
        except Exception as e: log_error(f"Failed to save knowledge base: {e}")

    def get_conversation_stats(self) -> Dict:
        total = len(self.conversations)
        by_intent = {}
        by_sentiment = {}
        for context in self.conversations.values():
            intent = context.intent.value
            sentiment = context.sentiment.value
            by_intent[intent] = by_intent.get(intent, 0) + 1
            by_sentiment[sentiment] = by_sentiment.get(sentiment, 0) + 1
        return {"active_conversations": total, "by_intent": by_intent, "by_sentiment": by_sentiment}

ai_cs_engine = AICSEngine()
__all__ = ["AICSEngine", "NLPProcessor", "Intent", "Sentiment", "ConversationContext", "ResponseTemplate", "ai_cs_engine"]