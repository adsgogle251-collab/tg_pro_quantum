"""
Unit tests for GroupVerificationService.
Tests all verification rules: format, channel detection, spam, member count, group type.
"""
import pytest

from app.services.group_verification import (
    GroupVerificationService,
    VerificationResult,
    group_verifier,
)


class TestGroupVerificationService:
    """Tests for GroupVerificationService."""

    def setup_method(self):
        self.service = GroupVerificationService()

    # ── verify_batch ─────────────────────────────────────────────────────────

    def test_verify_group_valid(self):
        results = self.service.verify_batch(["mygroup"])
        assert len(results) == 1
        assert results[0].verified is True
        assert results[0].username == "mygroup"

    def test_verify_group_strips_at_prefix(self):
        results = self.service.verify_batch(["@mygroup"])
        assert results[0].username == "mygroup"
        assert results[0].verified is True

    def test_verify_group_strips_whitespace(self):
        results = self.service.verify_batch(["  mygroup  "])
        assert results[0].username == "mygroup"
        assert results[0].verified is True

    def test_verify_channel_blocked(self):
        """Groups starting with channel_ are rejected."""
        results = self.service.verify_batch(["channel_news"])
        assert results[0].verified is False
        assert results[0].reason == "channel_not_allowed"
        assert "channel" in results[0].flags

    def test_verify_channel_suffix_blocked(self):
        """Groups ending with _channel are rejected."""
        results = self.service.verify_batch(["news_channel"])
        assert results[0].verified is False
        assert "channel" in results[0].flags

    def test_verify_invalid_username_format(self):
        """Usernames with invalid chars are rejected."""
        results = self.service.verify_batch(["invalid-name!"])
        assert results[0].verified is False
        assert results[0].reason == "invalid_username_format"

    def test_verify_empty_username(self):
        results = self.service.verify_batch([""])
        assert results[0].verified is False

    def test_verify_username_too_long(self):
        long_name = "a" * 33
        results = self.service.verify_batch([long_name])
        assert results[0].verified is False

    def test_verify_max_length_username_valid(self):
        username = "a" * 32
        results = self.service.verify_batch([username])
        assert results[0].verified is True

    def test_verify_duplicate_rejected(self):
        """Duplicate usernames in the same batch are flagged."""
        results = self.service.verify_batch(["mygroup", "mygroup"])
        assert results[0].verified is True
        assert results[1].verified is False
        assert results[1].reason == "duplicate"

    def test_verify_spam_keyword_flagged(self):
        """Usernames containing spam keywords are flagged as not verified."""
        results = self.service.verify_batch(["myspamgroup"])
        assert results[0].verified is False
        assert "spam_keyword" in results[0].flags

    def test_verify_member_count_below_minimum(self):
        """Groups with too few members are rejected."""
        meta = {"lowmembers": {"member_count": 5, "is_group": True}}
        results = self.service.verify_batch(["lowmembers"], metadata=meta, min_members=10)
        assert results[0].verified is False
        assert "low_members" in results[0].flags

    def test_verify_member_count_at_minimum(self):
        meta = {"mygroup": {"member_count": 10, "is_group": True}}
        results = self.service.verify_batch(["mygroup"], metadata=meta, min_members=10)
        assert results[0].verified is True

    def test_verify_is_not_group(self):
        """is_group=False causes rejection."""
        meta = {"notgroup": {"member_count": 500, "is_group": False}}
        results = self.service.verify_batch(["notgroup"], metadata=meta)
        assert results[0].verified is False
        assert results[0].reason == "not_a_group"

    def test_verify_with_valid_metadata(self):
        meta = {"validgroup": {"member_count": 500, "is_group": True}}
        results = self.service.verify_batch(["validgroup"], metadata=meta)
        assert results[0].verified is True
        assert results[0].member_count == 500
        assert results[0].is_group is True

    def test_verify_batch_multiple(self):
        usernames = ["group1", "group2", "channel_news", "invalid!"]
        results = self.service.verify_batch(usernames)
        assert results[0].verified is True
        assert results[1].verified is True
        assert results[2].verified is False  # channel
        assert results[3].verified is False  # invalid format

    def test_verify_custom_min_members(self):
        meta = {"biggroup": {"member_count": 50, "is_group": True}}
        results = self.service.verify_batch(["biggroup"], metadata=meta, min_members=100)
        assert results[0].verified is False

    # ── summary ───────────────────────────────────────────────────────────────

    def test_summary_counts(self):
        results = self.service.verify_batch(
            ["good_group", "channel_bad", "another_good"]
        )
        summary = self.service.summary(results)
        assert summary["total"] == 3
        assert summary["passed"] == 2
        assert summary["failed"] == 1
        assert len(summary["verified"]) == 3

    def test_summary_all_pass(self):
        results = self.service.verify_batch(["alpha", "beta", "gamma"])
        summary = self.service.summary(results)
        assert summary["passed"] == 3
        assert summary["failed"] == 0

    def test_summary_all_fail(self):
        results = self.service.verify_batch(
            ["channel_a", "channel_b"]
        )
        summary = self.service.summary(results)
        assert summary["passed"] == 0
        assert summary["failed"] == 2

    # ── VerificationResult.to_dict ────────────────────────────────────────────

    def test_to_dict_shape(self):
        r = VerificationResult(
            username="mygroup",
            verified=True,
            member_count=100,
            is_group=True,
        )
        d = r.to_dict()
        assert d["username"] == "mygroup"
        assert d["verified"] is True
        assert d["member_count"] == 100
        assert d["is_group"] is True
        assert d["reason"] is None
        assert d["flags"] == []

    # ── Singleton ─────────────────────────────────────────────────────────────

    def test_singleton_instance(self):
        assert group_verifier is not None
        assert isinstance(group_verifier, GroupVerificationService)

    # ── Edge cases ────────────────────────────────────────────────────────────

    def test_empty_batch(self):
        results = self.service.verify_batch([])
        assert results == []

    def test_lowercase_conversion(self):
        results = self.service.verify_batch(["@MyGroup"])
        assert results[0].username == "mygroup"

    def test_check_group_permissions_via_metadata(self):
        """No is_group metadata → no rejection on that rule."""
        meta = {"mygroup": {"member_count": 500}}
        results = self.service.verify_batch(["mygroup"], metadata=meta)
        assert results[0].verified is True

    def test_check_group_status_active(self):
        """Verify a group with normal metadata passes."""
        meta = {"activegroup": {"member_count": 200, "is_group": True}}
        results = self.service.verify_batch(["activegroup"], metadata=meta)
        assert results[0].verified is True
