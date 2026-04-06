"""
core/group_detector.py - Detect if Telegram entity is group vs channel
"""
from telethon.tl.types import Channel, Chat


def is_group(entity) -> bool:
    """Return True if entity is a group (not a broadcast channel)."""
    if isinstance(entity, Chat):
        return True
    if isinstance(entity, Channel):
        return bool(getattr(entity, "megagroup", False)) or not bool(
            getattr(entity, "broadcast", False)
        )
    return False


def get_entity_type(entity) -> str:
    """Return 'group', 'channel', or 'unknown'."""
    if isinstance(entity, Chat):
        return "group"
    if isinstance(entity, Channel):
        if getattr(entity, "broadcast", False):
            return "channel"
        return "group"
    return "unknown"


__all__ = ["is_group", "get_entity_type"]
