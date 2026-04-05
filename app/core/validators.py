"""
TG PRO QUANTUM - Email & Password Validators
"""
import re

EMAIL_RE = re.compile(r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$")
SPECIAL_CHARS = set("!@#$%^&*()_+-=[]{}|;':\",./<>?")


def validate_email_format(email: str) -> bool:
    """Return True if email matches a valid format."""
    return bool(EMAIL_RE.match(email))


def validate_password_strength(password: str) -> list[str]:
    """
    Validate password strength.

    Returns a list of error strings; empty list means password is valid.
    """
    errors: list[str] = []
    if len(password) < 8:
        errors.append("Password must be at least 8 characters long")
    if not any(c.isupper() for c in password):
        errors.append("Password must contain at least one uppercase letter")
    if not any(c.islower() for c in password):
        errors.append("Password must contain at least one lowercase letter")
    if not any(c.isdigit() for c in password):
        errors.append("Password must contain at least one digit")
    if not any(c in SPECIAL_CHARS for c in password):
        errors.append("Password must contain at least one special character (!@#$%^&* …)")
    return errors


def is_strong_password(password: str) -> bool:
    """Return True if password passes all strength checks."""
    return len(validate_password_strength(password)) == 0
