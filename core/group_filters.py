"""Advanced Group Filters - Filter Groups by Members, Activity, Keywords"""
import json
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional
from .utils import DATA_DIR, log, log_error

FILTERS_FILE = DATA_DIR / "group_filters.json"
GROUP_METADATA_FILE = DATA_DIR / "groups" / "metadata.json"

class GroupFilterManager:
    def __init__(self):
        self.filters_file = FILTERS_FILE
        self.metadata_file = GROUP_METADATA_FILE
        self.filters = {}
        self.group_metadata = {}
        self._load()
    
    def _load(self):
        """Load filters and metadata from files"""
        # Load filters
        if self.filters_file.exists():
            try:
                with open(self.filters_file, 'r', encoding='utf-8') as f:
                    self.filters = json.load(f)
                log(f"Loaded {len(self.filters)} group filters", "info")
            except Exception as e:
                log_error(f"Failed to load filters: {e}")
        
        # Load group metadata
        if self.metadata_file.exists():
            try:
                with open(self.metadata_file, 'r', encoding='utf-8') as f:
                    self.group_metadata = json.load(f)
                log(f"Loaded metadata for {len(self.group_metadata)} groups", "info")
            except Exception as e:
                log_error(f"Failed to load group metadata: {e}")
    
    def _save_filters(self):
        """Save filters to file"""
        try:
            self.filters_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.filters_file, 'w', encoding='utf-8') as f:
                json.dump(self.filters, f, indent=2, ensure_ascii=False)
        except Exception as e:
            log_error(f"Failed to save filters: {e}")
    
    def _save_metadata(self):
        """Save group metadata to file"""
        try:
            self.metadata_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.metadata_file, 'w', encoding='utf-8') as f:
                json.dump(self.group_metadata, f, indent=2, ensure_ascii=False)
        except Exception as e:
            log_error(f"Failed to save metadata: {e}")
    
    def create_filter(self, name: str, criteria: Dict) -> str:
        """Create new group filter"""
        import uuid
        filter_id = f"FLT_{uuid.uuid4().hex[:8].upper()}"
        
        filter_data = {
            "id": filter_id,
            "name": name,
            "criteria": criteria,
            "created_at": datetime.now().isoformat()
        }
        
        self.filters[filter_id] = filter_data
        self._save_filters()
        log(f"Filter created: {name} ({filter_id})", "success")
        return filter_id
    
    def get_filter(self, filter_id: str) -> Optional[Dict]:
        """Get filter by ID"""
        return self.filters.get(filter_id)
    
    def get_all_filters(self) -> List[Dict]:
        """Get all filters"""
        return list(self.filters.values())
    
    def delete_filter(self, filter_id: str) -> bool:
        """Delete filter"""
        if filter_id in self.filters:
            del self.filters[filter_id]
            self._save_filters()
            log(f"Filter deleted: {filter_id}", "info")
            return True
        return False
    
    def update_group_metadata(self, group_link: str, **kwargs):
        """Update metadata for a group"""
        if group_link not in self.group_metadata:
            self.group_metadata[group_link] = {
                "link": group_link,
                "first_seen": datetime.now().isoformat(),
                "last_activity": None,
                "member_count": 0,
                "activity_score": 0,
                "keywords": [],
                "tags": []
            }
        
        for key, value in kwargs.items():
            self.group_metadata[group_link][key] = value
        
        self.group_metadata[group_link]["last_updated"] = datetime.now().isoformat()
        self._save_metadata()
    
    def get_group_metadata(self, group_link: str) -> Optional[Dict]:
        """Get metadata for a group"""
        return self.group_metadata.get(group_link)
    
    def filter_groups(self, groups: List[str], filter_id: str) -> List[str]:
        """Filter groups based on filter criteria"""
        filter_data = self.get_filter(filter_id)
        if not filter_data:
            return groups
        
        criteria = filter_data["criteria"]
        filtered = []
        
        for group in groups:
            metadata = self.get_group_metadata(group)
            if not metadata:
                # No metadata, include by default
                filtered.append(group)
                continue
            
            # Apply criteria
            include = True
            
            # Min members
            if "min_members" in criteria:
                if metadata.get("member_count", 0) < criteria["min_members"]:
                    include = False
            
            # Max members
            if "max_members" in criteria and include:
                if metadata.get("member_count", 0) > criteria["max_members"]:
                    include = False
            
            # Keywords (must contain at least one)
            if "keywords" in criteria and include:
                group_text = f"{group} {' '.join(metadata.get('keywords', []))}".lower()
                if not any(kw.lower() in group_text for kw in criteria["keywords"]):
                    include = False
            
            # Exclude keywords (must not contain any)
            if "exclude_keywords" in criteria and include:
                group_text = f"{group} {' '.join(metadata.get('keywords', []))}".lower()
                if any(kw.lower() in group_text for kw in criteria["exclude_keywords"]):
                    include = False
            
            # Activity score
            if "min_activity_score" in criteria and include:
                if metadata.get("activity_score", 0) < criteria["min_activity_score"]:
                    include = False
            
            # Last activity
            if "active_within_days" in criteria and include:
                last_activity = metadata.get("last_activity")
                if last_activity:
                    last_dt = datetime.fromisoformat(last_activity)
                    days_since = (datetime.now() - last_dt).days
                    if days_since > criteria["active_within_days"]:
                        include = False
                else:
                    include = False
            
            if include:
                filtered.append(group)
        
        log(f"Filter '{filter_data['name']}': {len(filtered)}/{len(groups)} groups matched", "info")
        return filtered
    
    def get_all_metadata(self) -> Dict:
        """Get all group metadata"""
        return self.group_metadata
    
    def analyze_group_activity(self, group_link: str, messages_count: int, last_message_time: str):
        """Analyze and update group activity"""
        # Calculate activity score (0-100)
        activity_score = min(100, messages_count * 2)
        
        self.update_group_metadata(
            group_link,
            member_count=messages_count,  # Simplified - would need actual member count
            last_activity=last_message_time,
            activity_score=activity_score
        )
    
    def extract_keywords(self, group_link: str, group_name: str) -> List[str]:
        """Extract keywords from group name/description"""
        # Common spam/low-quality keywords to exclude
        spam_keywords = ["free", "giveaway", "win", "prize", "click here", "bitcoin", "crypto"]
        
        # Extract meaningful keywords
        words = re.findall(r'\b[a-zA-Z]{4,}\b', group_name.lower())
        keywords = [w for w in words if w not in spam_keywords]
        
        self.update_group_metadata(group_link, keywords=keywords)
        return keywords


# Global instance
group_filter_manager = GroupFilterManager()
__all__ = ["GroupFilterManager", "group_filter_manager"]