"""
TG PRO QUANTUM - Group Verification Service (Phase 3A)

Verifies that broadcast targets are real Telegram groups (not channels),
have sufficient members, are active, and show no spam indicators.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional

from app.utils.logger import get_logger

logger = get_logger(__name__)

# ── Constants ─────────────────────────────────────────────────────────────────

MIN_MEMBER_DEFAULT = 10
MAX_USERNAME_LEN = 32
SPAM_KEYWORDS = frozenset(
    ["spam", "ads", "promo_bot", "scam", "fake", "test123"]
)


# ── Data classes ─────────────────────────────────────────────────────────────

@dataclass
class VerificationResult:
    username: str
    verified: bool
    member_count: Optional[int] = None
    is_group: Optional[bool] = None
    reason: Optional[str] = None
    flags: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "username": self.username,
            "verified": self.verified,
            "member_count": self.member_count,
            "is_group": self.is_group,
            "reason": self.reason,
            "flags": self.flags,
        }


# ── Validator ─────────────────────────────────────────────────────────────────

class GroupVerificationService:
    """
    Validates a list of group usernames against a configurable ruleset.

    Rules (all must pass for verified=True):
      1. Username format valid (1–32 chars, alphanumeric + underscore)
      2. Not a known channel pattern (starts with channel_)
      3. Username does not contain spam keywords
      4. member_count >= min_members  (when metadata is provided)
      5. is_group == True             (when metadata is provided)
    """

    # ── Public API ────────────────────────────────────────────────────────────

    def verify_batch(
        self,
        usernames: List[str],
        metadata: Optional[dict] = None,
        min_members: int = MIN_MEMBER_DEFAULT,
    ) -> List[VerificationResult]:
        """
        Verify a batch of group usernames.

        Args:
            usernames:   List of Telegram group usernames (with or without @).
            metadata:    Optional dict keyed by username with keys
                         ``member_count`` (int) and ``is_group`` (bool).
                         When omitted the structural checks still run.
            min_members: Minimum member threshold (default 10).

        Returns:
            List of VerificationResult objects in the same order.
        """
        meta = metadata or {}
        results: List[VerificationResult] = []
        seen: set[str] = set()

        for raw in usernames:
            username = raw.lstrip("@").strip().lower()

            # Deduplication check
            if username in seen:
                results.append(VerificationResult(
                    username=username,
                    verified=False,
                    reason="duplicate",
                ))
                continue
            seen.add(username)

            result = self._verify_single(
                username, meta.get(username, {}), min_members
            )
            results.append(result)

        return results

    def summary(self, results: List[VerificationResult]) -> dict:
        """Return aggregated counts for a batch of results."""
        verified = [r for r in results if r.verified]
        return {
            "total": len(results),
            "passed": len(verified),
            "failed": len(results) - len(verified),
            "verified": [r.to_dict() for r in results],
        }

    # ── Private helpers ───────────────────────────────────────────────────────

    def _verify_single(
        self,
        username: str,
        meta: dict,
        min_members: int,
    ) -> VerificationResult:
        flags: List[str] = []

        # Rule 1: username format
        if not self._valid_username(username):
            return VerificationResult(
                username=username,
                verified=False,
                reason="invalid_username_format",
                flags=["invalid_format"],
            )

        # Rule 2: channel pattern detection
        if self._looks_like_channel(username):
            return VerificationResult(
                username=username,
                verified=False,
                reason="channel_not_allowed",
                flags=["channel"],
            )

        # Rule 3: spam keywords
        if self._has_spam_keyword(username):
            flags.append("spam_keyword")

        # Rule 4 & 5: optional metadata checks
        member_count: Optional[int] = meta.get("member_count")
        is_group: Optional[bool] = meta.get("is_group")

        if is_group is not None and not is_group:
            return VerificationResult(
                username=username,
                verified=False,
                member_count=member_count,
                is_group=is_group,
                reason="not_a_group",
                flags=flags + ["not_group"],
            )

        if member_count is not None and member_count < min_members:
            return VerificationResult(
                username=username,
                verified=False,
                member_count=member_count,
                is_group=is_group,
                reason=f"member_count_below_minimum ({member_count} < {min_members})",
                flags=flags + ["low_members"],
            )

        # Suspicious: has spam flags but not outright rejected → flag for review
        if flags:
            logger.warning("Group %s flagged for review: %s", username, flags)
            return VerificationResult(
                username=username,
                verified=False,
                member_count=member_count,
                is_group=is_group,
                reason="flagged_for_review",
                flags=flags,
            )

        return VerificationResult(
            username=username,
            verified=True,
            member_count=member_count,
            is_group=is_group,
        )

    @staticmethod
    def _valid_username(username: str) -> bool:
        return bool(re.fullmatch(r"[a-z0-9_]{1,32}", username))

    @staticmethod
    def _looks_like_channel(username: str) -> bool:
        """Heuristic: channels often start with 'channel_' or end in '_channel'."""
        return username.startswith("channel_") or username.endswith("_channel")

    @staticmethod
    def _has_spam_keyword(username: str) -> bool:
        return any(kw in username for kw in SPAM_KEYWORDS)


# Singleton
group_verifier = GroupVerificationService()
