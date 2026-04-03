"""TG PRO QUANTUM - Smart Scheduler with Reinforcement Learning"""
import json
import math
import random
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from .utils import DATA_DIR, log, log_error

SCHEDULER_FILE = DATA_DIR / "scheduler_rl.json"

@dataclass
class TimeSlot:
    hour: int
    day_of_week: int
    success_count: int = 0
    fail_count: int = 0
    engagement_score: float = 0.0
    last_tested: Optional[str] = None

    @property
    def success_rate(self) -> float:
        total = self.success_count + self.fail_count
        return self.success_count / total if total > 0 else 0.5

    @property
    def q_value(self) -> float:
        total = self.success_count + self.fail_count
        if total == 0: return 0.5
        exploration_bonus = math.sqrt(2 * math.log(total + 1) / (total + 1))
        return self.success_rate + 0.1 * exploration_bonus

    def update(self, success: bool, engagement: float = 50.0):
        if success: self.success_count += 1
        else: self.fail_count += 1
        alpha = 0.1
        self.engagement_score = (1 - alpha) * self.engagement_score + alpha * engagement
        self.last_tested = datetime.now().isoformat()

@dataclass
class SchedulerConfig:
    exploration_rate: float = 0.1
    learning_rate: float = 0.1
    discount_factor: float = 0.9
    min_samples_per_slot: int = 5
    timezone: str = "UTC"
    active_hours: Tuple[int, int] = (7, 23)
    preferred_days: List[int] = field(default_factory=lambda: [0, 1, 2, 3, 4])

class SmartSchedulerRL:
    def __init__(self):
        self.config_file = SCHEDULER_FILE
        self.config = SchedulerConfig()
        self.q_table: Dict[Tuple[int, int], TimeSlot] = {}
        self._init_time_slots()
        self._load()

    def _init_time_slots(self):
        for hour in range(24):
            for day in range(7):
                self.q_table[(hour, day)] = TimeSlot(hour=hour, day_of_week=day)

    def _load(self):
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                for key_str, slot_data in data.get("q_table", {}).items():
                    hour, day = map(int, key_str.split(","))
                    slot = self.q_table.get((hour, day))
                    if slot:
                        slot.success_count = slot_data.get("success_count", 0)
                        slot.fail_count = slot_data.get("fail_count", 0)
                        slot.engagement_score = slot_data.get("engagement_score", 0.0)
            except Exception as e: log_error(f"Failed to load scheduler: {e}")

    def _save(self):
        try:
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            data = {"q_table": {f"{hour},{day}": {"success_count": slot.success_count, "fail_count": slot.fail_count, "engagement_score": slot.engagement_score, "last_tested": slot.last_tested} for (hour, day), slot in self.q_table.items() if slot.success_count + slot.fail_count > 0}}
            with open(self.config_file, 'w', encoding='utf-8') as f: json.dump(data, f, indent=2)
        except Exception as e: log_error(f"Failed to save scheduler: {e}")

    def select_time(self, now: Optional[datetime] = None) -> datetime:
        if now is None: now = datetime.now()
        current_hour = now.hour
        current_day = now.weekday()
        valid_slots = [(hour, day) for (hour, day) in self.q_table.keys() if self.config.active_hours[0] <= hour < self.config.active_hours[1] and day in self.config.preferred_days]
        if not valid_slots: return now + timedelta(minutes=random.randint(5, 30))
        if random.random() < self.config.exploration_rate:
            hour, day = random.choice(valid_slots)
        else:
            best_slot = max(valid_slots, key=lambda slot: self.q_table[slot].q_value)
            hour, day = best_slot
        scheduled = now.replace(hour=hour, minute=0, second=0, microsecond=0)
        if scheduled <= now:
            days_ahead = (day - current_day + 7) % 7
            if days_ahead == 0 and hour <= current_hour: days_ahead = 7
            scheduled += timedelta(days=days_ahead)
        return scheduled

    def record_outcome(self, scheduled_time: datetime, success: bool, engagement: float = 50.0):
        hour = scheduled_time.hour
        day = scheduled_time.weekday()
        slot = self.q_table.get((hour, day))
        if not slot: return
        slot.update(success, engagement)
        self._save()

    def get_best_times(self, count: int = 5) -> List[Dict]:
        valid_slots = [(hour, day) for (hour, day) in self.q_table.keys() if self.config.active_hours[0] <= hour < self.config.active_hours[1] and day in self.config.preferred_days]
        sorted_slots = sorted(valid_slots, key=lambda slot: self.q_table[slot].q_value, reverse=True)[:count]
        return [{"hour": hour, "day": day, "day_name": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"][day], "q_value": round(self.q_table[(hour, day)].q_value, 3), "success_rate": round(self.q_table[(hour, day)].success_rate * 100, 1)} for hour, day in sorted_slots]

    def get_schedule_recommendation(self) -> Dict:
        best_times = self.get_best_times(3)
        return {"recommended_slots": best_times, "next_suggested": self.select_time().isoformat(), "confidence": self._calculate_overall_confidence(), "learning_progress": self._get_learning_progress()}

    def _calculate_overall_confidence(self) -> float:
        total_samples = sum(slot.success_count + slot.fail_count for slot in self.q_table.values())
        return min(0.95, total_samples / 500)

    def _get_learning_progress(self) -> Dict:
        tested_slots = sum(1 for slot in self.q_table.values() if slot.success_count + slot.fail_count >= self.config.min_samples_per_slot)
        total_slots = len([s for s in self.q_table.values() if self.config.active_hours[0] <= s.hour < self.config.active_hours[1]])
        return {"slots_tested": tested_slots, "slots_needed": self.config.min_samples_per_slot, "coverage_percent": round(tested_slots / max(1, total_slots) * 100, 1)}

smart_scheduler_rl = SmartSchedulerRL()
__all__ = ["SmartSchedulerRL", "SchedulerConfig", "TimeSlot", "smart_scheduler_rl"]