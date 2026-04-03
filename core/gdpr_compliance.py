"""TG PRO QUANTUM - GDPR Compliance"""
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, field, asdict
from .utils import DATA_DIR, log, log_error

GDPR_FILE = DATA_DIR / "gdpr_compliance.json"
CONSENT_FILE = DATA_DIR / "consent_records.json"
DATA_REQUESTS_FILE = DATA_DIR / "data_requests.json"

@dataclass
class ConsentRecord:
    user_id: str
    purpose: str
    granted: bool
    granted_at: str
    withdrawn_at: Optional[str] = None
    ip_address: str = ""
    version: str = "1.0"

    def to_dict(self) -> Dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict):
        return cls(**data)

@dataclass
class DataSubjectRequest:
    id: str
    user_id: str
    request_type: str
    status: str = "pending"
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    completed_at: Optional[str] = None
    response: str = ""

    def to_dict(self) -> Dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict):
        return cls(**data)

@dataclass
class DataRetention:
    data_type: str
    retention_period_days: int
    auto_delete: bool = True
    last_cleanup: Optional[str] = None

    def to_dict(self) -> Dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict):
        return cls(**data)

class GDPRCompliance:
    def __init__(self):
        self.consent_file = CONSENT_FILE
        self.requests_file = DATA_REQUESTS_FILE
        self.consent_records: Dict[str, ConsentRecord] = {}
        self.data_requests: Dict[str, DataSubjectRequest] = {}
        self.retention_policies: Dict[str, DataRetention] = {}
        self._load()
        self._init_retention_policies()

    def _load(self):
        if self.consent_file.exists():
            try:
                with open(self.consent_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for uid, cdata in data.items(): self.consent_records[uid] = ConsentRecord.from_dict(cdata)
            except: pass
        if self.requests_file.exists():
            try:
                with open(self.requests_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for rid, rdata in data.get("requests", {}).items(): self.data_requests[rid] = DataSubjectRequest.from_dict(rdata)
            except: pass

    def _save_consent(self):
        try:
            self.consent_file.parent.mkdir(parents=True, exist_ok=True)
            data = {uid: c.to_dict() for uid, c in self.consent_records.items()}
            with open(self.consent_file, 'w', encoding='utf-8') as f: json.dump(data, f, indent=2)
        except: pass

    def _save_requests(self):
        try:
            self.requests_file.parent.mkdir(parents=True, exist_ok=True)
            data = {"requests": {rid: r.to_dict() for rid, r in self.data_requests.items()}}
            with open(self.requests_file, 'w', encoding='utf-8') as f: json.dump(data, f, indent=2)
        except: pass

    def _init_retention_policies(self):
        self.retention_policies = {
            "user_data": DataRetention("user_data", 730, True),
            "broadcast_logs": DataRetention("broadcast_logs", 90, True),
            "audit_logs": DataRetention("audit_logs", 365, True),
            "session_data": DataRetention("session_data", 30, True),
        }

    def grant_consent(self, user_id: str, purpose: str, ip_address: str = "") -> bool:
        record = ConsentRecord(user_id=user_id, purpose=purpose, granted=True, granted_at=datetime.now().isoformat(), ip_address=ip_address)
        key = f"{user_id}:{purpose}"
        self.consent_records[key] = record
        self._save_consent()
        log(f"Consent granted: {user_id} for {purpose}", "success")
        return True

    def withdraw_consent(self, user_id: str, purpose: str) -> bool:
        key = f"{user_id}:{purpose}"
        record = self.consent_records.get(key)
        if not record: return False
        record.withdrawn_at = datetime.now().isoformat()
        record.granted = False
        self._save_consent()
        log(f"Consent withdrawn: {user_id} for {purpose}", "warning")
        return True

    def has_consent(self, user_id: str, purpose: str) -> bool:
        key = f"{user_id}:{purpose}"
        record = self.consent_records.get(key)
        if not record: return False
        return record.granted and record.withdrawn_at is None

    def create_data_request(self, user_id: str, request_type: str) -> str:
        import uuid
        request = DataSubjectRequest(id=f"DSR-{uuid.uuid4().hex[:8].upper()}", user_id=user_id, request_type=request_type)
        self.data_requests[request.id] = request
        self._save_requests()
        log(f"Data request created: {request.id}", "info")
        return request.id

    def complete_request(self, request_id: str, response: str = "") -> bool:
        request = self.data_requests.get(request_id)
        if not request: return False
        request.status = "completed"
        request.completed_at = datetime.now().isoformat()
        request.response = response
        self._save_requests()
        return True

    def right_to_access(self, user_id: str) -> Dict:
        return {"user_id": user_id, "consent_records": self.get_consent_records(user_id), "data_requests": [r.to_dict() for r in self.data_requests.values() if r.user_id == user_id], "collected_at": datetime.now().isoformat()}

    def right_to_erasure(self, user_id: str) -> bool:
        for key in list(self.consent_records.keys()):
            if key.startswith(f"{user_id}:"): self.withdraw_consent(user_id, key.split(":")[1])
        log(f"Erasure request processed for {user_id}", "warning")
        return True

    def get_consent_records(self, user_id: str) -> List[Dict]:
        return [r.to_dict() for k, r in self.consent_records.items() if k.startswith(f"{user_id}:")]

    def cleanup_expired_data(self) -> Dict:
        cleanup_stats = {"data_type": [], "records_deleted": 0, "last_cleanup": datetime.now().isoformat()}
        now = datetime.now()
        for data_type, policy in self.retention_policies.items():
            if not policy.auto_delete: continue
            cutoff = now - timedelta(days=policy.retention_period_days)
            deleted = 0
            for key, record in list(self.consent_records.items()):
                granted_at = datetime.fromisoformat(record.granted_at)
                if granted_at < cutoff:
                    del self.consent_records[key]
                    deleted += 1
            if deleted > 0:
                cleanup_stats["data_type"].append({"type": data_type, "deleted": deleted})
                cleanup_stats["records_deleted"] += deleted
                policy.last_cleanup = cleanup_stats["last_cleanup"]
        self._save_consent()
        log(f"Data cleanup: {cleanup_stats['records_deleted']} records deleted", "success")
        return cleanup_stats

    def get_compliance_report(self) -> Dict:
        return {"consent_records": len(self.consent_records), "active_consents": sum(1 for r in self.consent_records.values() if r.granted), "withdrawn_consents": sum(1 for r in self.consent_records.values() if r.withdrawn_at), "data_requests": {"total": len(self.data_requests), "pending": sum(1 for r in self.data_requests.values() if r.status == "pending"), "completed": sum(1 for r in self.data_requests.values() if r.status == "completed")}, "retention_policies": {k: v.to_dict() for k, v in self.retention_policies.items()}, "generated_at": datetime.now().isoformat()}

gdpr_compliance = GDPRCompliance()
__all__ = ["GDPRCompliance", "ConsentRecord", "DataSubjectRequest", "DataRetention", "gdpr_compliance"]