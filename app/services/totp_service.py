"""
TG PRO QUANTUM - TOTP / 2FA Service

Provides TOTP secret generation, QR-code URI building, and code verification
using the ``pyotp`` library (already in requirements.txt).

Backup codes are generated as random 8-character alphanumeric strings and
stored as bcrypt hashes so they can be verified without storing plaintext.
"""
from __future__ import annotations

import base64
import hashlib
import secrets
import string
from typing import List, Tuple

import pyotp

from app.utils.logger import get_logger

logger = get_logger(__name__)

_BACKUP_CODE_CHARS = string.ascii_uppercase + string.digits
_BACKUP_CODE_LEN = 8
_BACKUP_CODE_COUNT = 10
_ISSUER = "TG PRO QUANTUM"


class TOTPService:
    """Thin wrapper around ``pyotp`` with backup-code management."""

    # ── Secret generation ─────────────────────────────────────────────────────

    def generate_secret(self) -> str:
        """Return a new base32-encoded TOTP secret (32 chars → 160-bit)."""
        return pyotp.random_base32()

    def get_provisioning_uri(self, secret: str, account_label: str) -> str:
        """Return the ``otpauth://`` URI for QR-code display."""
        totp = pyotp.TOTP(secret)
        return totp.provisioning_uri(name=account_label, issuer_name=_ISSUER)

    # ── Code verification ─────────────────────────────────────────────────────

    def verify_code(self, secret: str, code: str, valid_window: int = 1) -> bool:
        """
        Verify a 6-digit TOTP code.

        *valid_window* allows ±1 time step (30 s) to accommodate slight clock drift.
        """
        totp = pyotp.TOTP(secret)
        result: bool = totp.verify(code, valid_window=valid_window)
        logger.debug("TOTP verify result=%s", result)
        return result

    # ── Backup codes ──────────────────────────────────────────────────────────

    def generate_backup_codes(self) -> Tuple[List[str], List[str]]:
        """
        Generate a fresh set of backup codes.

        Returns ``(plaintext_codes, hashed_codes)`` where hashed_codes is what
        should be persisted in the database.
        """
        plaintext: List[str] = [
            "".join(secrets.choice(_BACKUP_CODE_CHARS) for _ in range(_BACKUP_CODE_LEN))
            for _ in range(_BACKUP_CODE_COUNT)
        ]
        hashed = [self._hash_backup_code(c) for c in plaintext]
        return plaintext, hashed

    def verify_backup_code(self, code: str, stored_hashes: List[str]) -> Tuple[bool, List[str]]:
        """
        Verify a backup code against the stored hash list.

        Returns ``(valid, remaining_hashes)`` — the used hash is removed so each
        backup code can only be used once.
        """
        code_upper = code.strip().upper()
        code_hash = self._hash_backup_code(code_upper)
        if code_hash in stored_hashes:
            remaining = [h for h in stored_hashes if h != code_hash]
            return True, remaining
        return False, stored_hashes

    # ── Internal ──────────────────────────────────────────────────────────────

    @staticmethod
    def _hash_backup_code(code: str) -> str:
        """SHA-256 hex digest of the backup code (uppercased)."""
        return hashlib.sha256(code.upper().encode()).hexdigest()


totp_service = TOTPService()
