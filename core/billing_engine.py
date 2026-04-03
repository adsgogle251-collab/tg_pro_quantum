"""TG PRO QUANTUM - Billing Engine"""
import json
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass, field, asdict
from enum import Enum
from .utils import DATA_DIR, log, log_error

BILLING_FILE = DATA_DIR / "billing.json"

class SubscriptionTier(Enum):
    FREE = "free"
    STARTER = "starter"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"

class InvoiceStatus(Enum):
    DRAFT = "draft"
    SENT = "sent"
    PAID = "paid"
    OVERDUE = "overdue"
    CANCELLED = "cancelled"

PRICING = {
    SubscriptionTier.FREE: {"price": 0, "features": {"max_accounts": 5, "max_broadcasts_per_day": 100, "ai_features": False}},
    SubscriptionTier.STARTER: {"price": 499000, "features": {"max_accounts": 50, "max_broadcasts_per_day": 1000, "ai_features": True}},
    SubscriptionTier.PROFESSIONAL: {"price": 1499000, "features": {"max_accounts": 500, "max_broadcasts_per_day": 10000, "ai_features": True}},
    SubscriptionTier.ENTERPRISE: {"price": 4999000, "features": {"max_accounts": -1, "max_broadcasts_per_day": -1, "ai_features": True}},
}

@dataclass
class Subscription:
    id: str
    user_id: str
    tier: SubscriptionTier
    status: str = "active"
    started_at: str = field(default_factory=lambda: datetime.now().isoformat())
    expires_at: Optional[str] = None
    price: float = 0.0
    currency: str = "IDR"
    features: Dict = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {"id": self.id, "user_id": self.user_id, "tier": self.tier.value, "status": self.status, "started_at": self.started_at, "expires_at": self.expires_at, "price": self.price, "currency": self.currency, "features": self.features}

    @classmethod
    def from_dict(cls, data: Dict):
        data["tier"] = SubscriptionTier(data.get("tier", "free"))
        return cls(**data)

@dataclass
class Invoice:
    id: str
    subscription_id: str
    user_id: str
    amount: float
    currency: str = "IDR"
    status: InvoiceStatus = InvoiceStatus.DRAFT
    due_date: Optional[str] = None
    paid_date: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict:
        return {"id": self.id, "subscription_id": self.subscription_id, "user_id": self.user_id, "amount": self.amount, "currency": self.currency, "status": self.status.value, "due_date": self.due_date, "paid_date": self.paid_date, "created_at": self.created_at}

    @classmethod
    def from_dict(cls, data: Dict):
        data["status"] = InvoiceStatus(data.get("status", "draft"))
        return cls(**data)

class BillingEngine:
    def __init__(self):
        self.billing_file = BILLING_FILE
        self.subscriptions: Dict[str, Subscription] = {}
        self.invoices: Dict[str, Invoice] = {}
        self._load()

    def _load(self):
        if self.billing_file.exists():
            try:
                with open(self.billing_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for sid, sdata in data.get("subscriptions", {}).items(): self.subscriptions[sid] = Subscription.from_dict(sdata)
                    for iid, idata in data.get("invoices", {}).items(): self.invoices[iid] = Invoice.from_dict(idata)
            except Exception as e: log_error(f"Failed to load billing: {e}")

    def _save(self):
        try:
            self.billing_file.parent.mkdir(parents=True, exist_ok=True)
            data = {"subscriptions": {sid: s.to_dict() for sid, s in self.subscriptions.items()}, "invoices": {iid: i.to_dict() for iid, i in self.invoices.items()}}
            with open(self.billing_file, 'w', encoding='utf-8') as f: json.dump(data, f, indent=2)
        except Exception as e: log_error(f"Failed to save billing: {e}")

    def create_subscription(self, user_id: str, tier: SubscriptionTier, duration_months: int = 1) -> str:
        pricing = PRICING.get(tier, PRICING[SubscriptionTier.FREE])
        subscription = Subscription(id=str(uuid.uuid4())[:8], user_id=user_id, tier=tier, expires_at=(datetime.now() + timedelta(days=30 * duration_months)).isoformat(), price=pricing["price"] * duration_months, features=pricing["features"].copy())
        self.subscriptions[subscription.id] = subscription
        self._save()
        log(f"Subscription created: {user_id} - {tier.value}", "success")
        return subscription.id

    def get_subscription(self, user_id: str) -> Optional[Subscription]:
        now = datetime.now().isoformat()
        for sub in self.subscriptions.values():
            if sub.user_id == user_id and sub.status == "active":
                if not sub.expires_at or sub.expires_at > now: return sub
        return None

    def get_billing_stats(self) -> Dict:
        now = datetime.now().strftime("%Y-%m")
        monthly_revenue = sum(s.price for s in self.subscriptions.values() if s.status == "active")
        return {"total_subscriptions": len(self.subscriptions), "active_subscriptions": sum(1 for s in self.subscriptions.values() if s.status == "active"), "mrr": monthly_revenue, "total_revenue": sum(s.price for s in self.subscriptions.values())}

billing_engine = BillingEngine()
__all__ = ["BillingEngine", "Subscription", "Invoice", "SubscriptionTier", "InvoiceStatus", "PRICING", "billing_engine"]