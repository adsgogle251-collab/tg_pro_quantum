"""
core/keyword_generator.py - Generate 3-gram keyword combinations for group search
"""
from typing import List

PREFIXES = [
    "grup", "group", "komunitas", "community", "chat", "info", "official",
    "channel", "news", "diskusi", "forum", "update", "share", "jual",
    "beli", "loker", "bisnis", "business", "promosi", "promo",
]
SUFFIXES = [
    "indo", "indonesia", "id", "official", "grup", "group", "chat",
    "2024", "2025", "baru", "aktif", "ramai", "terbesar", "resmi",
    "public", "free", "open",
]


def generate_combinations(keyword: str, max_results: int = 2000) -> List[str]:
    """
    Generate keyword combinations for group searching.
    Returns list of search terms (keyword + prefix/suffix combos).
    """
    results: set[str] = set()
    kw = keyword.strip().lower()

    results.add(kw)

    for p in PREFIXES:
        results.add(f"{p} {kw}")
        results.add(f"{kw} {p}")
        results.add(f"{p}{kw}")
        results.add(f"{kw}{p}")

    for s in SUFFIXES:
        results.add(f"{kw} {s}")
        results.add(f"{s} {kw}")
        results.add(f"{kw}{s}")
        results.add(f"{s}{kw}")

    for p in PREFIXES[:10]:
        for s in SUFFIXES[:10]:
            results.add(f"{p} {kw} {s}")
            results.add(f"{kw} {p} {s}")

    words = kw.split()
    if len(words) > 1:
        for w in words:
            results.add(w)
            for p in PREFIXES[:8]:
                results.add(f"{p} {w}")
            for s in SUFFIXES[:8]:
                results.add(f"{w} {s}")

    results.discard("")
    return list(results)[:max_results]


__all__ = ["generate_combinations", "PREFIXES", "SUFFIXES"]
