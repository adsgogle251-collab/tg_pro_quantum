"""TG PRO QUANTUM - Predictive Analytics"""
import json
import math
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from .utils import DATA_DIR, log, log_error

PREDICTIONS_FILE = DATA_DIR / "predictions.json"

@dataclass
class PredictionResult:
    prediction: float
    confidence: float
    factors: Dict = field(default_factory=dict)
    recommendation: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict:
        return {"prediction": self.prediction, "confidence": self.confidence, "factors": self.factors, "recommendation": self.recommendation, "timestamp": self.timestamp}

class PredictiveAnalytics:
    def __init__(self):
        self.predictions_file = PREDICTIONS_FILE
        self._history: List[Dict] = []
        self._load_history()

    def _load_history(self):
        if self.predictions_file.exists():
            try:
                with open(self.predictions_file, 'r', encoding='utf-8') as f:
                    self._history = json.load(f)
            except: self._history = []

    def _save_history(self):
        try:
            self.predictions_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.predictions_file, 'w', encoding='utf-8') as f:
                json.dump(self._history[-1000:], f, indent=2)
        except: pass

    def predict_ban_risk(self, account_stats: Dict) -> PredictionResult:
        risk_score = 0.0
        if account_stats.get("messages_per_hour", 0) > 100: risk_score += 0.3
        if account_stats.get("error_rate", 0) > 0.1: risk_score += 0.3
        if account_stats.get("flood_count", 0) > 5: risk_score += 0.2
        if account_stats.get("account_age_days", 0) < 7: risk_score += 0.2
        risk_score = min(1.0, risk_score)
        if risk_score > 0.7: recommendation = "🔴 HIGH RISK: Reduce activity"
        elif risk_score > 0.4: recommendation = "🟡 MEDIUM RISK: Monitor closely"
        else: recommendation = "🟢 LOW RISK: Continue normal operations"
        result = PredictionResult(prediction=risk_score, confidence=0.7, factors=account_stats, recommendation=recommendation)
        self._history.append({"type": "ban_risk", "result": result.to_dict()})
        self._save_history()
        return result

    def predict_performance(self, account_stats: Dict) -> PredictionResult:
        score = 50.0
        if account_stats.get("success_rate", 0) > 0.9: score += 30
        elif account_stats.get("success_rate", 0) > 0.7: score += 15
        if account_stats.get("level", 1) >= 3: score += 10
        if account_stats.get("uptime_hours", 0) > 24: score += 10
        score = min(100, score)
        if score >= 90: recommendation = "🏆 Excellent performance"
        elif score >= 75: recommendation = "✅ Good performance"
        elif score >= 50: recommendation = "⚠️ Moderate performance"
        else: recommendation = "🔧 Low performance"
        result = PredictionResult(prediction=score, confidence=0.7, factors=account_stats, recommendation=recommendation)
        return result

    def predict_best_times(self, historical_data: List[Dict]) -> PredictionResult:
        if not historical_data:
            return PredictionResult(prediction=[9, 10, 11, 12, 13, 14, 19, 20], confidence=0.5, recommendation="Using default best hours")
        hour_stats = {}
        for entry in historical_data:
            hour = entry.get("hour", 0)
            success_rate = entry.get("success_rate", 0.5)
            if hour not in hour_stats: hour_stats[hour] = []
            hour_stats[hour].append(success_rate)
        hour_scores = {h: sum(scores)/len(scores) for h, scores in hour_stats.items()}
        best_hours = sorted(hour_scores.keys(), key=lambda h: hour_scores[h], reverse=True)[:8]
        return PredictionResult(prediction=best_hours, confidence=min(1.0, len(historical_data)/100), factors=hour_scores, recommendation=f"Best hours: {', '.join([f'{h:02d}:00' for h in best_hours[:5]])}")

    def forecast_revenue(self, current_metrics: Dict, days: int = 30) -> Dict:
        daily_rate = current_metrics.get("daily_revenue", 0)
        growth_rate = current_metrics.get("growth_rate", 0.02)
        forecast = []
        cumulative = 0
        for day in range(1, days + 1):
            daily = daily_rate * (1 + growth_rate) ** day
            cumulative += daily
            forecast.append({"day": day, "daily_revenue": round(daily, 2), "cumulative_revenue": round(cumulative, 2)})
        return {"forecast_days": days, "total_forecast": round(cumulative, 2), "daily_breakdown": forecast}

    def get_analytics_summary(self) -> Dict:
        return {"total_predictions": len(self._history), "last_updated": datetime.now().isoformat()}

predictive_analytics = PredictiveAnalytics()
__all__ = ["PredictiveAnalytics", "PredictionResult", "predictive_analytics"]