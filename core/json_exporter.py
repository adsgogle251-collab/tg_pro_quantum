"""TG PRO QUANTUM - JSON Exporter"""
import json
from pathlib import Path

class JSONExporter:
    def export_data(self, data, name, filepath):
        try:
            Path(filepath).parent.mkdir(parents=True, exist_ok=True)
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
        except: pass

json_exporter = JSONExporter()
__all__ = ["JSONExporter", "json_exporter"]