"""TG PRO QUANTUM - Cache Manager"""
from pathlib import Path

class CacheManager:
    def __init__(self):
        self.cache_dir = Path(__file__).parent.parent / "data" / "cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def clear_all(self):
        for file in self.cache_dir.glob("*"):
            if file.is_file(): file.unlink()

    def get_stats(self):
        try:
            total_size = sum(f.stat().st_size for f in self.cache_dir.glob("*") if f.is_file())
            return {"disk_size_mb": total_size / (1024 * 1024), "file_count": len(list(self.cache_dir.glob("*")))}
        except: return {"disk_size_mb": 0, "file_count": 0}

cache_manager = CacheManager()
__all__ = ["CacheManager", "cache_manager"]