"""TG PRO QUANTUM - A/B Testing Engine"""
import json
import math
import random
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum
from .utils import DATA_DIR, log, log_error

AB_TEST_FILE = DATA_DIR / "ab_tests.json"

class TestStatus(Enum):
    DRAFT = "draft"
    RUNNING = "running"
    COMPLETED = "completed"
    INCONCLUSIVE = "inconclusive"

class TestType(Enum):
    MESSAGE = "message"
    SCHEDULE = "schedule"
    AUDIENCE = "audience"

@dataclass
class TestVariant:
    name: str
    config: Dict
    traffic_allocation: float = 0.5
    impressions: int = 0
    successes: int = 0
    failures: int = 0

    @property
    def success_rate(self) -> float:
        total = self.successes + self.failures
        return self.successes / total if total > 0 else 0.0

    def to_dict(self) -> Dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict):
        return cls(**data)

@dataclass
class ABTest:
    id: str
    name: str
    test_type: TestType
    variants: List[TestVariant]
    status: TestStatus = TestStatus.DRAFT
    metric: str = "success_rate"
    min_sample_size: int = 100
    confidence_level: float = 0.95
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    winner: Optional[str] = None

    def to_dict(self) -> Dict:
        return {"id": self.id, "name": self.name, "test_type": self.test_type.value, "variants": [v.to_dict() for v in self.variants], "status": self.status.value, "metric": self.metric, "min_sample_size": self.min_sample_size, "confidence_level": self.confidence_level, "started_at": self.started_at, "completed_at": self.completed_at, "winner": self.winner}

    @classmethod
    def from_dict(cls, data: Dict):
        data["test_type"] = TestType(data.get("test_type", "message"))
        data["status"] = TestStatus(data.get("status", "draft"))
        data["variants"] = [TestVariant.from_dict(v) for v in data.get("variants", [])]
        return cls(**data)

class StatisticalAnalyzer:
    @staticmethod
    def z_test_proportions(p1: float, n1: int, p2: float, n2: int) -> Tuple[float, float]:
        if n1 == 0 or n2 == 0: return 0.0, 1.0
        p_pool = (p1 * n1 + p2 * n2) / (n1 + n2)
        se = math.sqrt(p_pool * (1 - p_pool) * (1/n1 + 1/n2))
        if se == 0: return 0.0, 1.0
        z = (p1 - p2) / se
        p_value = 2 * (1 - StatisticalAnalyzer._normal_cdf(abs(z)))
        return z, p_value

    @staticmethod
    def _normal_cdf(x: float) -> float:
        return 0.5 * (1 + math.erf(x / math.sqrt(2)))

    @staticmethod
    def determine_winner(test: ABTest) -> Optional[str]:
        if len(test.variants) < 2: return None
        for variant in test.variants:
            if variant.impressions < test.min_sample_size: return None
        control = test.variants[0]
        control_rate = control.success_rate
        best_variant = None
        best_improvement = 0
        for variant in test.variants[1:]:
            variant_rate = variant.success_rate
            z, p_value = StatisticalAnalyzer.z_test_proportions(control_rate, control.impressions, variant_rate, variant.impressions)
            alpha = 1 - test.confidence_level
            if p_value < alpha and variant_rate > control_rate:
                improvement = (variant_rate - control_rate) / control_rate if control_rate > 0 else 0
                if improvement > best_improvement:
                    best_improvement = improvement
                    best_variant = variant.name
        return best_variant

class ABTestingEngine:
    def __init__(self):
        self.test_file = AB_TEST_FILE
        self.tests: Dict[str, ABTest] = {}
        self._load()

    def _load(self):
        if self.test_file.exists():
            try:
                with open(self.test_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for tid, tdata in data.items():
                        self.tests[tid] = ABTest.from_dict(tdata)
            except Exception as e: log_error(f"Failed to load A/B tests: {e}")

    def _save(self):
        try:
            self.test_file.parent.mkdir(parents=True, exist_ok=True)
            data = {tid: t.to_dict() for tid, t in self.tests.items()}
            with open(self.test_file, 'w', encoding='utf-8') as f: json.dump(data, f, indent=2)
        except Exception as e: log_error(f"Failed to save A/B tests: {e}")

    def create_test(self, name: str, test_type: TestType, variants: List[Dict], metric: str = "success_rate") -> ABTest:
        import uuid
        test = ABTest(id=str(uuid.uuid4())[:8], name=name, test_type=test_type, variants=[TestVariant(name=v["name"], config=v["config"], traffic_allocation=v.get("traffic_allocation", 1.0 / len(variants))) for v in variants], metric=metric)
        self.tests[test.id] = test
        self._save()
        log(f"A/B test created: {name}", "success")
        return test

    def start_test(self, test_id: str) -> bool:
        test = self.tests.get(test_id)
        if not test or test.status != TestStatus.DRAFT: return False
        test.status = TestStatus.RUNNING
        test.started_at = datetime.now().isoformat()
        self._save()
        log(f"A/B test started: {test.name}", "info")
        return True

    def assign_variant(self, test_id: str) -> Optional[str]:
        test = self.tests.get(test_id)
        if not test or test.status != TestStatus.RUNNING: return None
        variants = test.variants
        weights = [v.traffic_allocation for v in variants]
        total = sum(weights)
        if total == 0: return variants[0].name
        weights = [w / total for w in weights]
        r = random.random()
        cumulative = 0
        for variant, weight in zip(variants, weights):
            cumulative += weight
            if r <= cumulative: return variant.name
        return variants[-1].name

    def record_impression(self, test_id: str, variant_name: str, success: bool, conversion: bool = False):
        test = self.tests.get(test_id)
        if not test: return
        variant = next((v for v in test.variants if v.name == variant_name), None)
        if not variant: return
        variant.impressions += 1
        if success: variant.successes += 1
        else: variant.failures += 1
        if conversion: variant.conversions += 1
        self._check_test_completion(test)
        self._save()

    def _check_test_completion(self, test: ABTest):
        if test.status != TestStatus.RUNNING: return
        if any(v.impressions < test.min_sample_size for v in test.variants): return
        winner = StatisticalAnalyzer.determine_winner(test)
        if winner:
            test.status = TestStatus.COMPLETED
            test.winner = winner
            test.completed_at = datetime.now().isoformat()
            log(f"A/B test completed: {test.name} - Winner: {winner}", "success")
        elif self._has_run_long_enough(test):
            test.status = TestStatus.INCONCLUSIVE
            test.completed_at = datetime.now().isoformat()
            log(f"A/B test completed: {test.name} - Inconclusive", "info")

    def _has_run_long_enough(self, test: ABTest, min_hours: int = 24) -> bool:
        if not test.started_at: return False
        started = datetime.fromisoformat(test.started_at)
        elapsed = datetime.now() - started
        return elapsed.total_seconds() >= min_hours * 3600

    def get_test_results(self, test_id: str) -> Dict:
        test = self.tests.get(test_id)
        if not test: return {}
        results = {"test_id": test_id, "name": test.name, "status": test.status.value, "metric": test.metric, "variants": []}
        for variant in test.variants:
            results["variants"].append({"name": variant.name, "impressions": variant.impressions, "success_rate": round(variant.success_rate * 100, 2)})
        if test.status == TestStatus.COMPLETED:
            results["winner"] = test.winner
        return results

    def get_active_tests(self) -> List[ABTest]:
        return [t for t in self.tests.values() if t.status == TestStatus.RUNNING]

    def stop_test(self, test_id: str) -> bool:
        test = self.tests.get(test_id)
        if not test or test.status != TestStatus.RUNNING: return False
        test.status = TestStatus.INCONCLUSIVE
        test.completed_at = datetime.now().isoformat()
        self._save()
        return True

    def get_recommendations(self) -> List[Dict]:
        recommendations = []
        for test in self.tests.values():
            if test.status == TestStatus.COMPLETED and test.winner:
                winner = next((v for v in test.variants if v.name == test.winner), None)
                if winner:
                    recommendations.append({"test_name": test.name, "winner": test.winner, "config": winner.config, "action": f"Apply '{test.winner}' configuration"})
        return recommendations

ab_testing_engine = ABTestingEngine()
__all__ = ["ABTestingEngine", "StatisticalAnalyzer", "ABTest", "TestVariant", "TestStatus", "TestType", "ab_testing_engine"]