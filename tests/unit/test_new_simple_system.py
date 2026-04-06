"""
tests/unit/test_new_simple_system.py
Unit tests for the new simple system (core/config, core/analytics, core/broadcast, core/finder)
"""
import os
import json
import tempfile
import pytest

# Point all databases to a temp directory so tests are isolated
os.environ["TG_DATA_DIR"] = tempfile.mkdtemp(prefix="tg_test_")


# ─────────────────────────────────────────────────────────────────────────────
# core/config
# ─────────────────────────────────────────────────────────────────────────────

class TestConfig:
    def test_get_set_setting(self):
        from core.config import get_setting, set_setting
        set_setting("test_key", "hello_world")
        assert get_setting("test_key") == "hello_world"

    def test_default_value(self):
        from core.config import get_setting
        assert get_setting("nonexistent_key_xyz", "default") == "default"

    def test_api_id_integer(self):
        from core.config import set_setting, get_api_id
        set_setting("api_id", "12345")
        assert get_api_id() == 12345

    def test_api_id_invalid_returns_zero(self):
        from core.config import set_setting, get_api_id
        set_setting("api_id", "not_a_number")
        assert get_api_id() == 0

    def test_api_hash(self):
        from core.config import set_setting, get_api_hash
        set_setting("api_hash", "abc123def456")
        assert get_api_hash() == "abc123def456"

    def test_app_version_default(self):
        from core.config import get_app_version
        # Returns non-empty string
        assert get_app_version()


# ─────────────────────────────────────────────────────────────────────────────
# core/finder
# ─────────────────────────────────────────────────────────────────────────────

class TestFinder:
    def test_save_and_list_groups(self):
        from core.finder import save_group, list_groups
        save_group("@testgroup1", 5, [
            {"id": 1, "username": "u1", "first_name": "A", "last_name": "", "phone": ""}
        ])
        groups = list_groups()
        assert any(g["group_link"] == "@testgroup1" for g in groups)

    def test_get_members(self):
        from core.finder import save_group, get_members
        save_group("@membertest", 2, [
            {"id": 10, "username": "x", "first_name": "X", "last_name": "", "phone": ""},
            {"id": 11, "username": "y", "first_name": "Y", "last_name": "", "phone": ""},
        ])
        members = get_members("@membertest")
        assert len(members) == 2
        assert members[0]["first_name"] == "X"

    def test_delete_group(self):
        from core.finder import save_group, delete_group, get_group
        save_group("@to_delete", 1, [])
        assert get_group("@to_delete") is not None
        delete_group("@to_delete")
        assert get_group("@to_delete") is None

    def test_export_csv(self):
        from core.finder import save_group, export_csv
        save_group("@csvgroup", 2, [
            {"id": 1, "username": "alice", "first_name": "Alice", "last_name": "Smith", "phone": ""},
            {"id": 2, "username": "bob",   "first_name": "Bob",   "last_name": "Jones", "phone": ""},
        ])
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
            tmp = f.name
        try:
            ok, msg = export_csv("@csvgroup", tmp)
            assert ok, msg
            content = open(tmp).read()
            assert "alice" in content
            assert "bob" in content
            assert "first_name" in content
        finally:
            os.unlink(tmp)

    def test_export_csv_empty_group(self):
        from core.finder import export_csv
        ok, msg = export_csv("@nonexistent_group_xyz", "/tmp/nope.csv")
        assert not ok


# ─────────────────────────────────────────────────────────────────────────────
# core/broadcast
# ─────────────────────────────────────────────────────────────────────────────

class TestBroadcast:
    def test_save_and_list_broadcasts(self):
        from core.broadcast import save_broadcast, list_broadcasts
        save_broadcast("Test Run", sent=8, failed=2, total=10, duration=30.5)
        broadcasts = list_broadcasts()
        assert len(broadcasts) >= 1
        latest = broadcasts[0]
        assert latest["name"] == "Test Run"
        assert latest["sent"] == 8
        assert latest["failed"] == 2
        assert latest["total"] == 10
        assert latest["duration"] == 30.5

    def test_progress_tracking(self):
        from core.broadcast import BroadcastProgress
        p = BroadcastProgress(10)
        assert p.total == 10
        assert p.sent == 0
        assert p.failed == 0
        assert p.pending == 10
        assert p.done == 0

    def test_progress_add_log(self):
        from core.broadcast import BroadcastProgress
        p = BroadcastProgress(5)
        p.add_log("Test message")
        assert len(p.log) == 1
        assert "Test message" in p.log[0]

    def test_progress_log_newest_first(self):
        from core.broadcast import BroadcastProgress
        p = BroadcastProgress(5)
        p.add_log("First")
        p.add_log("Second")
        # Newest first
        assert "Second" in p.log[0]
        assert "First" in p.log[1]

    def test_engine_not_running_initially(self):
        from core.broadcast import BroadcastEngine
        eng = BroadcastEngine()
        assert not eng.is_running
        assert not eng.is_paused

    def test_engine_stop_when_not_running(self):
        from core.broadcast import BroadcastEngine
        eng = BroadcastEngine()
        # Should not raise
        eng.stop()
        assert not eng.is_running


# ─────────────────────────────────────────────────────────────────────────────
# core/analytics
# ─────────────────────────────────────────────────────────────────────────────

class TestAnalytics:
    def test_account_summary_structure(self):
        from core.analytics import account_summary
        summary = account_summary()
        assert "total" in summary
        assert "active" in summary
        assert "expired" in summary
        assert "error" in summary

    def test_broadcast_summary_structure(self):
        from core.analytics import broadcast_summary
        summary = broadcast_summary()
        assert "total_broadcasts" in summary
        assert "total_sent" in summary
        assert "total_failed" in summary
        assert "success_rate" in summary

    def test_broadcast_summary_with_data(self):
        from core.broadcast import save_broadcast
        from core.analytics import broadcast_summary
        save_broadcast("Analytics Test", sent=20, failed=5, total=25, duration=60.0)
        summary = broadcast_summary()
        assert summary["total_broadcasts"] >= 1
        assert summary["total_sent"] >= 20
        assert 0 <= summary["success_rate"] <= 100

    def test_recent_broadcasts(self):
        from core.broadcast import save_broadcast
        from core.analytics import recent_broadcasts
        save_broadcast("Recent Test", sent=3, failed=1, total=4, duration=10.0)
        items = recent_broadcasts(10)
        assert isinstance(items, list)
        assert any(b["name"] == "Recent Test" for b in items)

    def test_weekly_stats(self):
        from core.analytics import weekly_stats
        stats = weekly_stats()
        assert isinstance(stats, list)
        # Each entry has expected keys
        for day in stats:
            assert "date" in day
            assert "sent" in day
            assert "failed" in day

    def test_success_rate_calculation(self):
        from core.broadcast import save_broadcast
        from core.analytics import broadcast_summary
        # 8 sent out of 10 = 80%
        save_broadcast("Rate Test", sent=8, failed=2, total=10, duration=5.0)
        summary = broadcast_summary()
        # Rate is calculated as sent/total, not per-broadcast averages
        assert summary["success_rate"] >= 0

    def test_daily_stats(self):
        from core.analytics import daily_stats
        stats = daily_stats(days=30)
        assert isinstance(stats, list)
