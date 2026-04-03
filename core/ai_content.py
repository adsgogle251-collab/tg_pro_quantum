"""TG PRO QUANTUM - AI Content Generator"""
import asyncio
import random
import re
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
from .utils import DATA_DIR, log, log_error

AI_CONFIG_FILE = DATA_DIR / "ai_config.json"

class AIContentGenerator:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        self.config_file = AI_CONFIG_FILE
        self.config = self._load_config()
        self._client = None
        if api_key:
            try:
                import openai
                openai.api_key = api_key
                self._client = openai
                log("AI Client initialized", "success")
            except ImportError:
                log("OpenAI not available, using templates", "warning")

    def _load_config(self) -> Dict:
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f: return json.load(f)
            except: pass
        return {"model": "gpt-3.5-turbo", "temperature": 0.7, "max_tokens": 500, "language": "id", "tone": "professional"}

    def _save_config(self):
        try:
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_file, 'w', encoding='utf-8') as f: json.dump(self.config, f, indent=2)
        except: pass

    def set_config(self, **kwargs):
        self.config.update(kwargs)
        self._save_config()

    async def generate_message(self, topic: str, content_type: str = "broadcast", tone: str = "professional", length: str = "medium") -> List[str]:
        if not self._client or not self.api_key:
            return self._generate_template_message(topic, content_type, tone, length)
        prompt = self._build_prompt(topic, content_type, tone, length)
        try:
            response = await asyncio.to_thread(self._client.ChatCompletion.create, model=self.config.get("model", "gpt-3.5-turbo"), messages=[{"role": "system", "content": "You are a professional marketing copywriter."}, {"role": "user", "content": prompt}], temperature=self.config.get("temperature", 0.7), max_tokens=self.config.get("max_tokens", 500))
            content = response.choices[0].message.content.strip()
            variations = [v.strip() for v in content.split('\n\n') if v.strip()]
            log_success(f"AI generated {len(variations)} message variations")
            return variations if variations else [content]
        except Exception as e:
            log_error(f"AI generation failed: {e}")
            return self._generate_template_message(topic, content_type, tone, length)

    def _build_prompt(self, topic: str, content_type: str, tone: str, length: str) -> str:
        length_map = {"short": "50-100 words", "medium": "100-200 words", "long": "200-400 words"}
        return f"""Create a Telegram broadcast message about: {topic}
Requirements:
- Type: {content_type}
- Tone: {tone}
- Length: {length_map.get(length, "100-200 words")}
- Language: {self.config.get("language", "Indonesian")}
- Include emojis appropriately
- Add a clear call-to-action
Generate 3 variations."""

    def _generate_template_message(self, topic: str, content_type: str, tone: str, length: str) -> List[str]:
        templates = {
            "promo": [f"🔥 {topic.upper()}! 🔥\n\nDapatkan penawaran spesial hari ini!\n\n👉 Klik: https://t.me/channel", f"⚡ PROMO TERBATAS ⚡\n\n{topic}\n\nJangan lewatkan!\n\n🔗 Link: https://t.me/channel"],
            "info": [f"📢 INFO PENTING 📢\n\n{topic}\n\nSilakan dibaca!\n\nTerima kasih!", f"📋 Pengumuman\n\n{topic}\n\nMohon perhatiannya."],
            "broadcast": [f"🚀 {topic}\n\n{self._generate_body(length)}\n\n👉 Action: https://t.me/link"],
        }
        template_type = "broadcast"
        for key in templates:
            if key in content_type.lower() or key in topic.lower(): template_type = key
        return templates.get(template_type, templates["broadcast"])

    def _generate_body(self, length: str) -> str:
        bodies = {"short": "Ini pesan singkat untuk broadcast Anda.", "medium": "Ini pesan dengan panjang sedang. Anda bisa menambahkan detail produk atau layanan di sini.", "long": "Ini pesan panjang. Anda bisa menjelaskan detail produk, manfaat, fitur, testimoni, dan informasi lengkap lainnya."}
        return bodies.get(length, bodies["medium"])

    async def rewrite_message(self, message: str, style: str = "anti_spam") -> str:
        if style == "anti_spam": return self._anti_spam_rewrite(message)
        elif style == "humanize": return self._humanize_message(message)
        return message

    def _anti_spam_rewrite(self, message: str) -> str:
        spam_triggers = {"FREE": "gratis", "100%": "seratus persen", "!!!": "!", "CLICK HERE": "klik di sini", "LIMITED TIME": "waktu terbatas"}
        result = message
        for trigger, replacement in spam_triggers.items():
            result = re.sub(re.escape(trigger), replacement, result, flags=re.IGNORECASE)
        return result

    def _humanize_message(self, message: str) -> str:
        openers = ["Hai!", "Halo!", "Hei!", "Pagi!", "Siang!"]
        closers = ["Terima kasih!", "Salam!", "Semoga membantu!", "🙏"]
        lines = message.split('\n')
        if not any(lines[0].startswith(o) for o in openers): lines.insert(0, random.choice(openers))
        if not any(lines[-1].startswith(c) for c in closers): lines.append(random.choice(closers))
        return '\n'.join(lines)

    def analyze_spam_score(self, message: str) -> Dict[str, float]:
        score = 0.0
        factors = {}
        if message.count('!') > 3 or message.count('?') > 3:
            score += 0.2
            factors["excessive_punctuation"] = 0.2
        if sum(1 for c in message if c.isupper()) / len(message) > 0.5:
            score += 0.15
            factors["excessive_caps"] = 0.15
        spam_words = ["free", "gratis", "win", "winner", "prize", "click here", "act now", "limited"]
        message_lower = message.lower()
        spam_count = sum(1 for word in spam_words if word in message_lower)
        if spam_count > 2:
            score += 0.25
            factors["spam_keywords"] = 0.25
        factors["total_score"] = min(1.0, score)
        return factors

    def generate_variations(self, base_message: str, count: int = 3) -> List[str]:
        variations = [base_message]
        for _ in range(count - 1):
            variant = base_message
            emojis = ["🔥", "✨", "🚀", "💎", "⭐", "🎯", "💫", "🎁", "📢", "⚡"]
            variant = re.sub(r'[🔥✨🚀💎⭐🎯💫🎁📢⚡]', lambda m: random.choice(emojis), variant)
            if variant not in variations: variations.append(variant)
        return variations

# Global instance
ai_content = AIContentGenerator()
AIContentGenerator = AIContentGenerator

__all__ = ["AIContentGenerator", "ai_content"]