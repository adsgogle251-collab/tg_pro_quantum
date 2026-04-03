"""TG PRO QUANTUM - AI Account Manager"""
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, field, asdict
from enum import Enum
from .utils import DATA_DIR, log, log_error
from .account_manager import account_manager
from .predictive_analytics import predictive_analytics

ACCOUNT_AI_FILE = DATA_DIR / "account_ai.json"

class AccountHealthStatus(Enum):
    EXCELLENT = "excellent"
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"
    CRITICAL = "critical"

class WarmingStrategy(Enum):
    CONSERVATIVE = "conservative"
    BALANCED = "balanced"
    AGGRESSIVE = "aggressive"

@dataclass
class WarmingSchedule:
    strategy: WarmingStrategy = WarmingStrategy.BALANCED
    daily_join_limit: int = 20
    daily_message_limit: int = 10
    delay_min: int = 120
    delay_max: int = 600
    active_hours: tuple = (7, 23)

    def get_limits_for_level(self, level: int) -> Dict:
        multipliers = {1: 0.5, 2: 1.0, 3: 2.0, 4: 4.0}
        mult = multipliers.get(level, 1.0)
        return {"join_per_day": int(self.daily_join_limit * mult), "message_per_day": int(self.daily_message_limit * mult), "delay_min": max(30, int(self.delay_min / mult)), "delay_max": max(60, int(self.delay_max / mult))}

@dataclass
class AccountAIData:
    account_id: str
    health_status: AccountHealthStatus = AccountHealthStatus.GOOD
    ban_risk_score: float = 0.0
    performance_score: float = 75.0
    warming_progress: float = 0.0
    current_level: int = 1
    warming_schedule: WarmingSchedule = field(default_factory=WarmingSchedule)
    today_joins: int = 0
    today_messages: int = 0
    last_activity: Optional[str] = None
    recommended_action: str = "continue"
    last_updated: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict:
        return {"account_id": self.account_id, "health_status": self.health_status.value, "ban_risk_score": self.ban_risk_score, "performance_score": self.performance_score, "warming_progress": self.warming_progress, "current_level": self.current_level, "warming_schedule": asdict(self.warming_schedule), "today_joins": self.today_joins, "today_messages": self.today_messages, "last_activity": self.last_activity, "recommended_action": self.recommended_action, "last_updated": self.last_updated}

    @classmethod
    def from_dict(cls, data: Dict):
        data["health_status"] = AccountHealthStatus(data.get("health_status", "good"))
        data["warming_schedule"] = WarmingSchedule(**data.get("warming_schedule", {}))
        return cls(**data)

class AIAccountManager:
    def __init__(self):
        self.ai_file = ACCOUNT_AI_FILE
        self.accounts: Dict[str, AccountAIData] = {}
        self._load()

    def _load(self):
        if self.ai_file.exists():
            try:
                with open(self.ai_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for aid, adata in data.items():
                        self.accounts[aid] = AccountAIData.from_dict(adata)
            except Exception as e: log_error(f"Failed to load AI data: {e}")

    def _save(self):
        try:
            self.ai_file.parent.mkdir(parents=True, exist_ok=True)
            data = {aid: a.to_dict() for aid, a in self.accounts.items()}
            with open(self.ai_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
        except Exception as e: log_error(f"Failed to save AI data: {e}")

    def get_or_create(self, account_id: str) -> AccountAIData:
        if account_id not in self.accounts:
            self.accounts[account_id] = AccountAIData(account_id=account_id)
            self._save()
        return self.accounts[account_id]

    def update_health(self, account_id: str, stats: Dict) -> AccountHealthStatus:
        ai_data = self.get_or_create(account_id)
        ban_pred = predictive_analytics.predict_ban_risk(stats)
        ai_data.ban_risk_score = ban_pred.prediction
        perf_pred = predictive_analytics.predict_performance(stats)
        ai_data.performance_score = perf_pred.prediction
        if ai_data.ban_risk_score > 0.7 or ai_data.performance_score < 30: ai_data.health_status = AccountHealthStatus.CRITICAL
        elif ai_data.ban_risk_score > 0.5 or ai_data.performance_score < 50: ai_data.health_status = AccountHealthStatus.POOR
        elif ai_data.ban_risk_score > 0.3 or ai_data.performance_score < 70: ai_data.health_status = AccountHealthStatus.FAIR
        elif ai_data.performance_score >= 90: ai_data.health_status = AccountHealthStatus.EXCELLENT
        else: ai_data.health_status = AccountHealthStatus.GOOD
        ai_data.recommended_action = self._generate_recommendation(ai_data)
        ai_data.last_updated = datetime.now().isoformat()
        self._save()
        return ai_data.health_status

    def _generate_recommendation(self, ai_data: AccountAIData) -> str:
        if ai_data.health_status == AccountHealthStatus.CRITICAL: return "pause_and_review"
        elif ai_data.health_status == AccountHealthStatus.POOR: return "reduce_activity"
        elif ai_data.warming_progress < 100 and ai_data.current_level < 4: return "continue_warming"
        elif ai_data.performance_score >= 90: return "scale_up"
        else: return "maintain_current"

    def should_send(self, account_id: str) -> tuple:
        ai_data = self.get_or_create(account_id)
        if ai_data.health_status in [AccountHealthStatus.CRITICAL, AccountHealthStatus.POOR]:
            return False, f"Account health: {ai_data.health_status.value}"
        limits = ai_data.warming_schedule.get_limits_for_level(ai_data.current_level)
        if ai_data.today_messages >= limits["message_per_day"]:
            return False, "Daily message limit reached"
        current_hour = datetime.now().hour
        if not (ai_data.warming_schedule.active_hours[0] <= current_hour < ai_data.warming_schedule.active_hours[1]):
            return False, "Outside active hours"
        return True, "OK"

    def record_activity(self, account_id: str, action: str, success: bool):
        ai_data = self.get_or_create(account_id)
        ai_data.last_activity = datetime.now().isoformat()
        if action == "message": ai_data.today_messages += 1
        if success:
            ai_data.performance_score = min(100, ai_data.performance_score + 0.5)
            if ai_data.warming_progress < 100:
                ai_data.warming_progress = min(100, ai_data.warming_progress + 0.5)
                if ai_data.warming_progress >= 100 and ai_data.current_level < 4:
                    ai_data.current_level += 1
                    ai_data.warming_progress = 0
                    log(f"Account {account_id} leveled up to {ai_data.current_level}!", "success")
        else:
            ai_data.performance_score = max(0, ai_data.performance_score - 2)
        if ai_data.last_activity:
            last_dt = datetime.fromisoformat(ai_data.last_activity)
            if last_dt.date() < datetime.now().date():
                ai_data.today_joins = 0
                ai_data.today_messages = 0
        self._save()

    def get_all_accounts_status(self) -> List[Dict]:
        return [{"account_id": aid, "health": adata.health_status.value, "ban_risk": round(adata.ban_risk_score, 2), "performance": round(adata.performance_score, 1), "level": adata.current_level, "warming": round(adata.warming_progress, 1)} for aid, adata in self.accounts.items()]

ai_account_manager = AIAccountManager()
__all__ = ["AIAccountManager", "AccountAIData", "WarmingSchedule", "WarmingStrategy", "AccountHealthStatus", "ai_account_manager"]