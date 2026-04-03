"""TG PRO QUANTUM - CRM Engine"""
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass, field, asdict
from enum import Enum
from .utils import DATA_DIR, log, log_error

CRM_FILE = DATA_DIR / "crm.json"

class ContactStatus(Enum):
    LEAD = "lead"
    PROSPECT = "prospect"
    CUSTOMER = "customer"
    VIP = "vip"
    CHURNED = "churned"

class DealStage(Enum):
    NEW = "new"
    QUALIFIED = "qualified"
    PROPOSAL = "proposal"
    NEGOTIATION = "negotiation"
    CLOSED_WON = "closed_won"
    CLOSED_LOST = "closed_lost"

class TaskPriority(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"

@dataclass
class Contact:
    id: str
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    company: Optional[str] = None
    status: ContactStatus = ContactStatus.LEAD
    tags: List[str] = field(default_factory=list)
    notes: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    total_value: float = 0.0

    def to_dict(self) -> Dict:
        return {"id": self.id, "name": self.name, "email": self.email, "phone": self.phone, "company": self.company, "status": self.status.value, "tags": self.tags, "notes": self.notes, "created_at": self.created_at, "updated_at": self.updated_at, "total_value": self.total_value}

    @classmethod
    def from_dict(cls, data: Dict):
        data["status"] = ContactStatus(data.get("status", "lead"))
        return cls(**data)

@dataclass
class Deal:
    id: str
    title: str
    contact_id: str
    value: float
    stage: DealStage = DealStage.NEW
    probability: float = 0.0
    expected_close: Optional[str] = None
    owner_id: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict:
        return {"id": self.id, "title": self.title, "contact_id": self.contact_id, "value": self.value, "stage": self.stage.value, "probability": self.probability, "expected_close": self.expected_close, "owner_id": self.owner_id, "created_at": self.created_at, "updated_at": self.updated_at}

    @classmethod
    def from_dict(cls, data: Dict):
        data["stage"] = DealStage(data.get("stage", "new"))
        return cls(**data)

@dataclass
class Task:
    id: str
    title: str
    description: str = ""
    priority: TaskPriority = TaskPriority.MEDIUM
    due_date: Optional[str] = None
    assigned_to: str = ""
    contact_id: Optional[str] = None
    deal_id: Optional[str] = None
    status: str = "pending"
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    completed_at: Optional[str] = None

    def to_dict(self) -> Dict:
        return {"id": self.id, "title": self.title, "description": self.description, "priority": self.priority.value, "due_date": self.due_date, "assigned_to": self.assigned_to, "contact_id": self.contact_id, "deal_id": self.deal_id, "status": self.status, "created_at": self.created_at, "completed_at": self.completed_at}

    @classmethod
    def from_dict(cls, data: Dict):
        data["priority"] = TaskPriority(data.get("priority", "medium"))
        return cls(**data)

class CRMEngine:
    def __init__(self):
        self.crm_file = CRM_FILE
        self.contacts: Dict[str, Contact] = {}
        self.deals: Dict[str, Deal] = {}
        self.tasks: Dict[str, Task] = {}
        self._load()

    def _load(self):
        if self.crm_file.exists():
            try:
                with open(self.crm_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for cid, cdata in data.get("contacts", {}).items(): self.contacts[cid] = Contact.from_dict(cdata)
                    for did, ddata in data.get("deals", {}).items(): self.deals[did] = Deal.from_dict(ddata)
                    for tid, tdata in data.get("tasks", {}).items(): self.tasks[tid] = Task.from_dict(tdata)
            except Exception as e: log_error(f"Failed to load CRM: {e}")

    def _save(self):
        try:
            self.crm_file.parent.mkdir(parents=True, exist_ok=True)
            data = {"contacts": {cid: c.to_dict() for cid, c in self.contacts.items()}, "deals": {did: d.to_dict() for did, d in self.deals.items()}, "tasks": {tid: t.to_dict() for tid, t in self.tasks.items()}}
            with open(self.crm_file, 'w', encoding='utf-8') as f: json.dump(data, f, indent=2)
        except Exception as e: log_error(f"Failed to save CRM: {e}")

    def create_contact(self, name: str, email: Optional[str] = None, phone: Optional[str] = None, company: Optional[str] = None) -> str:
        import uuid
        contact = Contact(id=str(uuid.uuid4())[:8], name=name, email=email, phone=phone, company=company)
        self.contacts[contact.id] = contact
        self._save()
        log(f"Contact created: {name}", "success")
        return contact.id

    def create_deal(self, title: str, contact_id: str, value: float, owner_id: str = "") -> str:
        import uuid
        deal = Deal(id=str(uuid.uuid4())[:8], title=title, contact_id=contact_id, value=value, owner_id=owner_id, probability=0.2 if contact_id else 0.1)
        self.deals[deal.id] = deal
        self._save()
        log(f"Deal created: {title} (${value})", "success")
        return deal.id

    def create_task(self, title: str, description: str = "", priority: TaskPriority = TaskPriority.MEDIUM, due_date: Optional[str] = None, assigned_to: str = "") -> str:
        import uuid
        task = Task(id=str(uuid.uuid4())[:8], title=title, description=description, priority=priority, due_date=due_date, assigned_to=assigned_to)
        self.tasks[task.id] = task
        self._save()
        log(f"Task created: {title}", "success")
        return task.id

    def get_crm_stats(self) -> Dict:
        pipeline_value = {stage.value: sum(d.value for d in self.deals.values() if d.stage == stage) for stage in DealStage}
        return {"total_contacts": len(self.contacts), "total_deals": len(self.deals), "pipeline_value": pipeline_value, "total_pipeline_value": sum(pipeline_value.values()), "total_tasks": len(self.tasks), "pending_tasks": sum(1 for t in self.tasks.values() if t.status == "pending")}

crm_engine = CRMEngine()
__all__ = ["CRMEngine", "Contact", "Deal", "Task", "ContactStatus", "DealStage", "TaskPriority", "crm_engine"]