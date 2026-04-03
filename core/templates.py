"""Message Templates Manager - Save & Reuse Broadcast Messages"""
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
from .utils import DATA_DIR, log, log_error

TEMPLATES_FILE = DATA_DIR / "templates.json"

class TemplateManager:
    def __init__(self):
        self.templates_file = TEMPLATES_FILE
        self.templates: Dict[str, dict] = {}
        self._load()
    
    def _load(self):
        """Load templates from file"""
        if self.templates_file.exists():
            try:
                with open(self.templates_file, 'r', encoding='utf-8') as f:
                    self.templates = json.load(f)
                log(f"Loaded {len(self.templates)} message templates", "info")
            except Exception as e:
                log_error(f"Failed to load templates: {e}")
                self.templates = {}
    
    def _save(self):
        """Save templates to file"""
        try:
            self.templates_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.templates_file, 'w', encoding='utf-8') as f:
                json.dump(self.templates, f, indent=2, ensure_ascii=False)
        except Exception as e:
            log_error(f"Failed to save templates: {e}")
    
    def create_template(self, name: str, content: str, category: str = "general",
                        variables: List[str] = None, description: str = "") -> str:
        """Create new message template"""
        import uuid
        template_id = f"TPL_{uuid.uuid4().hex[:8].upper()}"
        
        template = {
            "id": template_id,
            "name": name,
            "content": content,
            "category": category,
            "variables": variables or [],
            "description": description,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "usage_count": 0
        }
        
        self.templates[template_id] = template
        self._save()
        log(f"Template created: {name} ({template_id})", "success")
        return template_id
    
    def get_template(self, template_id: str) -> Optional[dict]:
        """Get template by ID"""
        return self.templates.get(template_id)
    
    def get_all_templates(self, category: str = None) -> List[dict]:
        """Get all templates, optionally filtered by category"""
        if category:
            return [t for t in self.templates.values() if t["category"] == category]
        return list(self.templates.values())
    
    def update_template(self, template_id: str, **kwargs) -> bool:
        """Update template fields"""
        template = self.templates.get(template_id)
        if not template:
            return False
        
        for key, value in kwargs.items():
            if key in template:
                template[key] = value
        
        template["updated_at"] = datetime.now().isoformat()
        self._save()
        return True
    
    def delete_template(self, template_id: str) -> bool:
        """Delete template"""
        if template_id in self.templates:
            del self.templates[template_id]
            self._save()
            log(f"Template deleted: {template_id}", "info")
            return True
        return False
    
    def render_template(self, template_id: str, **variables) -> str:
        """Render template with variable substitution"""
        template = self.get_template(template_id)
        if not template:
            return ""
        
        content = template["content"]
        
        # Replace {variable} with actual values
        for key, value in variables.items():
            content = content.replace(f"{{{key}}}", str(value))
        
        # Track usage
        template["usage_count"] = template.get("usage_count", 0) + 1
        self._save()
        
        return content
    
    def get_categories(self) -> List[str]:
        """Get all template categories"""
        categories = set(t["category"] for t in self.templates.values())
        return list(categories)


# Global instance
template_manager = TemplateManager()
__all__ = ["TemplateManager", "template_manager"]