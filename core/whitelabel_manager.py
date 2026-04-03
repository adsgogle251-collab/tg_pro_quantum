"""TG PRO QUANTUM - White-Label Manager"""
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, field, asdict
from .utils import DATA_DIR, log, log_error

WHITELABEL_FILE = DATA_DIR / "whitelabel.json"
BRANDING_FILE = DATA_DIR / "branding.json"

@dataclass
class BrandingConfig:
    app_name: str = "TG PRO AI QUANTUM"
    company_name: str = "TG PRO Team"
    company_logo: str = ""
    company_url: str = "https://tgpro.com"
    support_email: str = "support@tgpro.com"
    primary_color: str = "#6366f1"
    secondary_color: str = "#e94560"
    bg_dark: str = "#1a1a2e"
    hide_tgpro_branding: bool = False
    custom_favicon: str = ""

    def to_dict(self) -> Dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict):
        return cls(**data)

@dataclass
class ResellerLicense:
    id: str
    company_name: str
    contact_email: str
    max_clients: int
    commission_rate: float = 0.2
    status: str = "active"
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    expires_at: Optional[str] = None
    clients: List[str] = field(default_factory=list)
    total_revenue: float = 0.0
    total_commission: float = 0.0

    def to_dict(self) -> Dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict):
        return cls(**data)

class WhiteLabelManager:
    def __init__(self):
        self.whitelabel_file = WHITELABEL_FILE
        self.branding_file = BRANDING_FILE
        self.branding = BrandingConfig()
        self.resellers: Dict[str, ResellerLicense] = {}
        self._load()

    def _load(self):
        if self.branding_file.exists():
            try:
                with open(self.branding_file, 'r', encoding='utf-8') as f:
                    self.branding = BrandingConfig.from_dict(json.load(f))
            except: pass
        if self.whitelabel_file.exists():
            try:
                with open(self.whitelabel_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for rid, rdata in data.get("resellers", {}).items():
                        self.resellers[rid] = ResellerLicense.from_dict(rdata)
            except: pass

    def _save_branding(self):
        try:
            self.branding_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.branding_file, 'w', encoding='utf-8') as f: json.dump(self.branding.to_dict(), f, indent=2)
        except: pass

    def _save_resellers(self):
        try:
            self.whitelabel_file.parent.mkdir(parents=True, exist_ok=True)
            data = {"resellers": {rid: r.to_dict() for rid, r in self.resellers.items()}}
            with open(self.whitelabel_file, 'w', encoding='utf-8') as f: json.dump(data, f, indent=2)
        except: pass

    def update_branding(self, **kwargs) -> bool:
        for key, value in kwargs.items():
            if hasattr(self.branding, key): setattr(self.branding, key, value)
        self._save_branding()
        log("Branding updated", "success")
        return True

    def get_branding(self) -> Dict:
        return self.branding.to_dict()

    def create_reseller_license(self, company_name: str, contact_email: str, max_clients: int, commission_rate: float = 0.2, duration_months: int = 12) -> str:
        reseller = ResellerLicense(id=f"RES-{uuid.uuid4().hex[:8].upper()}", company_name=company_name, contact_email=contact_email, max_clients=max_clients, commission_rate=commission_rate, expires_at=(datetime.now() + timedelta(days=30 * duration_months)).isoformat())
        self.resellers[reseller.id] = reseller
        self._save_resellers()
        log(f"Reseller license created: {reseller.id}", "success")
        return reseller.id

    def get_reseller_stats(self, reseller_id: str) -> Dict:
        reseller = self.resellers.get(reseller_id)
        if not reseller: return {}
        return {"id": reseller.id, "company_name": reseller.company_name, "status": reseller.status, "clients_count": len(reseller.clients), "max_clients": reseller.max_clients, "total_revenue": reseller.total_revenue, "total_commission": reseller.total_commission}

whitelabel_manager = WhiteLabelManager()
__all__ = ["WhiteLabelManager", "BrandingConfig", "ResellerLicense", "whitelabel_manager"]