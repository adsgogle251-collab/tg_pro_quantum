"""
core/ban_detector.py - Ban detection, logging, and suggestions
"""
from core.config import log_ban, list_ban_logs

BAN_ERRORS = {
    "UserBannedInChannelError": "Banned by admin",
    "ChatWriteForbiddenError": "Forbidden to write",
    "ChatAdminRequiredError": "Admin privileges required",
    "UserNotParticipantError": "Not a participant (kicked)",
    "PeerFloodError": "Flood limit - too many actions",
}

SUGGESTIONS = {
    "UserBannedInChannelError": "leave",
    "ChatWriteForbiddenError": "leave",
    "ChatAdminRequiredError": "leave",
    "UserNotParticipantError": "leave",
    "PeerFloodError": "wait",
}


def detect_ban(exception) -> str | None:
    """Return ban type string if exception is a ban error, else None."""
    error_name = type(exception).__name__
    return BAN_ERRORS.get(error_name)


def get_suggestion(exception) -> str:
    """Get action suggestion for a ban exception."""
    error_name = type(exception).__name__
    return SUGGESTIONS.get(error_name, "ignore")


def record_ban(phone: str, group_link: str, exception) -> str:
    """
    Record a ban event and return the suggestion.
    Returns 'leave', 'wait', or 'ignore'.
    """
    reason = type(exception).__name__
    suggestion = get_suggestion(exception)
    log_ban(phone, group_link, reason)
    return suggestion


def get_ban_summary() -> dict:
    """Return summary stats for ban logs."""
    logs = list_ban_logs()
    summary: dict = {
        "total": len(logs),
        "by_reason": {},
        "by_account": {},
        "suggest_leave": 0,
        "suggest_wait": 0,
    }
    for entry in logs:
        reason = entry.get("reason", "unknown")
        phone = entry.get("account_phone", "unknown")
        summary["by_reason"][reason] = summary["by_reason"].get(reason, 0) + 1
        summary["by_account"][phone] = summary["by_account"].get(phone, 0) + 1

        suggestion = SUGGESTIONS.get(reason, "ignore")
        if suggestion == "leave":
            summary["suggest_leave"] += 1
        elif suggestion == "wait":
            summary["suggest_wait"] += 1

    return summary


__all__ = [
    "detect_ban",
    "get_suggestion",
    "record_ban",
    "get_ban_summary",
    "BAN_ERRORS",
    "SUGGESTIONS",
]
