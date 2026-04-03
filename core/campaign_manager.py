"""Campaign Manager - Complete with Auto-Save"""
import json
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from enum import Enum
from typing import List, Dict, Optional
from dataclasses import dataclass, field, asdict
from .utils import DATA_DIR, log, log_error

CAMPAIGNS_FILE = DATA_DIR / "campaigns.json"

class CampaignStatus(Enum):
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"

class CampaignType(Enum):
    IMMEDIATE = "immediate"
    SCHEDULED = "scheduled"
    RECURRING = "recurring"

@dataclass
class CampaignMessage:
    text: str = ""
    image_path: Optional[str] = None
    has_image: bool = False

@dataclass
class CampaignSchedule:
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    recurring_days: List[str] = field(default_factory=list)
    recurring_time: Optional[str] = None

@dataclass
class CampaignSettings:
    delay_min: int = 10
    delay_max: int = 30
    round_robin: bool = True
    auto_retry: bool = True
    max_retries: int = 3
    rate_limit_per_hour: int = 100
    stop_on_error: bool = False
    auto_scrape: bool = False

@dataclass
class CampaignStats:
    total_groups: int = 0
    messages_sent: int = 0
    messages_failed: int = 0
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    last_error: Optional[str] = None

@dataclass
class Campaign:
    id: str
    name: str
    status: CampaignStatus = CampaignStatus.DRAFT
    campaign_type: CampaignType = CampaignType.IMMEDIATE
    message: CampaignMessage = field(default_factory=CampaignMessage)
    schedule: CampaignSchedule = field(default_factory=CampaignSchedule)
    settings: CampaignSettings = field(default_factory=CampaignSettings)
    account_ids: List[str] = field(default_factory=list)
    group_ids: List[str] = field(default_factory=list)
    group_source: str = "joined"
    stats: CampaignStats = field(default_factory=CampaignStats)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "name": self.name,
            "status": self.status.value,
            "campaign_type": self.campaign_type.value,
            "message": {
                "text": self.message.text,
                "image_path": self.message.image_path,
                "has_image": self.message.has_image
            },
            "schedule": {
                "start_time": self.schedule.start_time,
                "end_time": self.schedule.end_time,
                "recurring_days": self.schedule.recurring_days,
                "recurring_time": self.schedule.recurring_time
            },
            "settings": {
                "delay_min": self.settings.delay_min,
                "delay_max": self.settings.delay_max,
                "round_robin": self.settings.round_robin,
                "auto_retry": self.settings.auto_retry,
                "max_retries": self.settings.max_retries,
                "rate_limit_per_hour": self.settings.rate_limit_per_hour,
                "stop_on_error": self.settings.stop_on_error,
                "auto_scrape": self.settings.auto_scrape
            },
            "account_ids": self.account_ids,
            "group_ids": self.group_ids,
            "group_source": self.group_source,
            "stats": {
                "total_groups": self.stats.total_groups,
                "messages_sent": self.stats.messages_sent,
                "messages_failed": self.stats.messages_failed,
                "started_at": self.stats.started_at,
                "completed_at": self.stats.completed_at,
                "last_error": self.stats.last_error
            },
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "Campaign":
        return cls(
            id=data["id"],
            name=data["name"],
            status=CampaignStatus(data.get("status", "draft")),
            campaign_type=CampaignType(data.get("campaign_type", "immediate")),
            message=CampaignMessage(
                text=data.get("message", {}).get("text", ""),
                image_path=data.get("message", {}).get("image_path"),
                has_image=data.get("message", {}).get("has_image", False)
            ),
            schedule=CampaignSchedule(
                start_time=data.get("schedule", {}).get("start_time"),
                end_time=data.get("schedule", {}).get("end_time"),
                recurring_days=data.get("schedule", {}).get("recurring_days", []),
                recurring_time=data.get("schedule", {}).get("recurring_time")
            ),
            settings=CampaignSettings(
                delay_min=data.get("settings", {}).get("delay_min", 10),
                delay_max=data.get("settings", {}).get("delay_max", 30),
                round_robin=data.get("settings", {}).get("round_robin", True),
                auto_retry=data.get("settings", {}).get("auto_retry", True),
                max_retries=data.get("settings", {}).get("max_retries", 3),
                rate_limit_per_hour=data.get("settings", {}).get("rate_limit_per_hour", 100),
                stop_on_error=data.get("settings", {}).get("stop_on_error", False),
                auto_scrape=data.get("settings", {}).get("auto_scrape", False)
            ),
            account_ids=data.get("account_ids", []),
            group_ids=data.get("group_ids", []),
            group_source=data.get("group_source", "joined"),
            stats=CampaignStats(
                total_groups=data.get("stats", {}).get("total_groups", 0),
                messages_sent=data.get("stats", {}).get("messages_sent", 0),
                messages_failed=data.get("stats", {}).get("messages_failed", 0),
                started_at=data.get("stats", {}).get("started_at"),
                completed_at=data.get("stats", {}).get("completed_at"),
                last_error=data.get("stats", {}).get("last_error")
            ),
            created_at=data.get("created_at", datetime.now().isoformat()),
            updated_at=data.get("updated_at", datetime.now().isoformat())
        )


class CampaignManager:
    def __init__(self):
        self.campaigns_file = CAMPAIGNS_FILE
        self.campaigns: Dict[str, Campaign] = {}
        self._load()

    def _load(self):
        """Load campaigns from file"""
        if self.campaigns_file.exists():
            try:
                with open(self.campaigns_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for cid, cdata in data.get("campaigns", {}).items():
                        self.campaigns[cid] = Campaign.from_dict(cdata)
                log(f"Loaded {len(self.campaigns)} campaigns", "info")
            except Exception as e:
                log_error(f"Failed to load campaigns: {e}")
                self.campaigns = {}

    def _save(self):
        """Save campaigns to file"""
        try:
            self.campaigns_file.parent.mkdir(parents=True, exist_ok=True)
            data = {
                "campaigns": {cid: c.to_dict() for cid, c in self.campaigns.items()},
                "last_updated": datetime.now().isoformat()
            }
            with open(self.campaigns_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            log_error(f"Failed to save campaigns: {e}")

    def create_campaign(self, name: str) -> Campaign:
        """Create new campaign"""
        campaign_id = str(uuid.uuid4())[:8].upper()
        campaign = Campaign(id=campaign_id, name=name)
        self.campaigns[campaign_id] = campaign
        self._save()
        log(f"Campaign created: {name} ({campaign_id})", "success")
        return campaign

    def get_campaign(self, campaign_id: str) -> Optional[Campaign]:
        """Get campaign by ID"""
        return self.campaigns.get(campaign_id)

    def get_all_campaigns(self) -> List[Campaign]:
        """Get all campaigns"""
        return list(self.campaigns.values())

    def update_campaign(self, campaign_id: str, **kwargs) -> bool:
        """Update campaign fields with AUTO-SAVE"""
        campaign = self.campaigns.get(campaign_id)
        if not campaign:
            return False
        
        for key, value in kwargs.items():
            if hasattr(campaign, key):
                setattr(campaign, key, value)
        
        campaign.updated_at = datetime.now().isoformat()
        self._save()  # AUTO-SAVE
        log(f"Campaign updated: {campaign.name}", "success")
        return True

    def delete_campaign(self, campaign_id: str) -> bool:
        """Delete campaign"""
        if campaign_id in self.campaigns:
            del self.campaigns[campaign_id]
            self._save()
            log(f"Campaign deleted: {campaign_id}", "info")
            return True
        return False

    def start_campaign(self, campaign_id: str) -> bool:
        """Start campaign"""
        campaign = self.campaigns.get(campaign_id)
        if not campaign:
            return False
        
        campaign.status = CampaignStatus.RUNNING
        campaign.stats.started_at = datetime.now().isoformat()
        self._save()
        log(f"Campaign started: {campaign.name}", "success")
        return True

    def pause_campaign(self, campaign_id: str) -> bool:
        """Pause campaign"""
        campaign = self.campaigns.get(campaign_id)
        if not campaign:
            return False
        
        campaign.status = CampaignStatus.PAUSED
        self._save()
        log(f"Campaign paused: {campaign.name}", "warning")
        return True

    def stop_campaign(self, campaign_id: str) -> bool:
        """Stop campaign"""
        campaign = self.campaigns.get(campaign_id)
        if not campaign:
            return False
        
        campaign.status = CampaignStatus.COMPLETED
        campaign.stats.completed_at = datetime.now().isoformat()
        self._save()
        log(f"Campaign stopped: {campaign.name}", "info")
        return True

    def get_running_campaigns(self) -> List[Campaign]:
        """Get all running campaigns"""
        return [c for c in self.campaigns.values() if c.status == CampaignStatus.RUNNING]

    def get_campaign_summary(self) -> Dict:
        """Get campaign summary statistics"""
        campaigns = list(self.campaigns.values())
        return {
            "total": len(campaigns),
            "draft": sum(1 for c in campaigns if c.status == CampaignStatus.DRAFT),
            "running": sum(1 for c in campaigns if c.status == CampaignStatus.RUNNING),
            "paused": sum(1 for c in campaigns if c.status == CampaignStatus.PAUSED),
            "completed": sum(1 for c in campaigns if c.status == CampaignStatus.COMPLETED),
            "total_messages_sent": sum(c.stats.messages_sent for c in campaigns),
            "total_messages_failed": sum(c.stats.messages_failed for c in campaigns)
        }


# Global instance
campaign_manager = CampaignManager()
__all__ = ["CampaignManager", "Campaign", "CampaignStatus", "CampaignType", "campaign_manager"]