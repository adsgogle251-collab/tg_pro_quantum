"""
TG PRO QUANTUM - General-purpose helpers
"""
import hashlib
import hmac
import random
import secrets
import string
from datetime import datetime, timezone


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def generate_api_key(length: int = 40) -> str:
    """Cryptographically-secure API key (alphanumeric)."""
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def generate_otp(digits: int = 6) -> str:
    """Generate a numeric OTP code."""
    return "".join(str(random.SystemRandom().randint(0, 9)) for _ in range(digits))


def safe_username(value: str) -> str:
    """Extract a clean Telegram username from a URL or @handle."""
    value = value.strip()
    if "t.me/" in value:
        value = value.split("t.me/")[1].split("?")[0]
    if value.startswith("@"):
        value = value[1:]
    return value.strip("/").lower()


def constant_time_compare(val1: str, val2: str) -> bool:
    """Timing-attack-safe string comparison."""
    return hmac.compare_digest(
        hashlib.sha256(val1.encode()).digest(),
        hashlib.sha256(val2.encode()).digest(),
    )
