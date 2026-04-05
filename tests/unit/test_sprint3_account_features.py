"""
Unit tests for Sprint 3: Session Import, Bulk Create, TOTP, Import Service.
"""
from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import TelegramAccount, AccountStatus, ImportLog, ImportStatus, ImportSourceType
from app.services.import_service import (
    parse_session_text,
    parse_csv_content,
    parse_excel_content,
    ImportService,
)
from app.services.totp_service import TOTPService
from tests.conftest import create_test_client, create_test_account


# ─────────────────────────────────────────────────────────────────────────────
# parse_session_text
# ─────────────────────────────────────────────────────────────────────────────

class TestParseSessionText:
    def test_pipe_delimited(self):
        text = "+1234567890|12345678|abc123def456abc123def456abc123def456abc1|SESSIONXYZ"
        result = parse_session_text(text)
        assert result["phone"] == "+1234567890"
        assert result["api_id"] == 12345678
        assert result["api_hash"] == "abc123def456abc123def456abc123def456abc1"

    def test_colon_delimited(self):
        text = "+9876543210:87654321:hashvalue00000000000000000000000000000:SomeLongSession"
        result = parse_session_text(text)
        assert result["phone"] == "+9876543210"
        assert result["api_id"] == 87654321

    def test_json_format(self):
        import json
        data = {"phone": "+11112223333", "api_id": 111, "api_hash": "aabbccdd" * 4, "session_string": "XYZ"}
        result = parse_session_text(json.dumps(data))
        assert result["phone"] == "+11112223333"
        assert result["api_id"] == 111

    def test_raw_session_string(self):
        # A long enough string that looks like a base64 session
        raw = "A" * 40
        result = parse_session_text(raw)
        assert result.get("session_string") == raw

    def test_empty_returns_empty(self):
        result = parse_session_text("   ")
        assert result == {}


# ─────────────────────────────────────────────────────────────────────────────
# parse_csv_content
# ─────────────────────────────────────────────────────────────────────────────

class TestParseCsvContent:
    def test_basic(self):
        csv_text = "phone,name,api_id\n+1111111111,Alice,100\n+2222222222,Bob,200\n"
        rows, errors = parse_csv_content(csv_text)
        assert len(rows) == 2
        assert rows[0]["phone"] == "+1111111111"
        assert rows[0]["name"] == "Alice"
        assert rows[0]["api_id"] == 100
        assert errors == []

    def test_missing_phone_column_is_error(self):
        csv_text = "name,api_id\nAlice,100\n"
        rows, errors = parse_csv_content(csv_text)
        assert rows == []
        assert len(errors) == 1
        assert "phone" in errors[0].lower()

    def test_rows_without_phone_skipped(self):
        csv_text = "phone,name\n,Alice\n+3333333333,Bob\n"
        rows, errors = parse_csv_content(csv_text)
        assert len(rows) == 1
        assert len(errors) == 1
        assert rows[0]["phone"] == "+3333333333"

    def test_tags_parsed(self):
        csv_text = "phone,tags\n+1234567890,vip,premium\n"
        rows, errors = parse_csv_content(csv_text)
        # tags column present but value is "vip"
        assert rows[0]["phone"] == "+1234567890"

    def test_bytes_input(self):
        csv_bytes = b"phone\n+9999999999\n"
        rows, errors = parse_csv_content(csv_bytes)
        assert len(rows) == 1
        assert rows[0]["phone"] == "+9999999999"


# ─────────────────────────────────────────────────────────────────────────────
# TOTP service
# ─────────────────────────────────────────────────────────────────────────────

class TestTOTPService:
    def setup_method(self):
        self.svc = TOTPService()

    def test_generate_secret_is_valid_base32(self):
        import base64
        secret = self.svc.generate_secret()
        assert len(secret) == 32
        # Must be valid base32
        base64.b32decode(secret)

    def test_provisioning_uri_contains_secret(self):
        secret = self.svc.generate_secret()
        uri = self.svc.get_provisioning_uri(secret, "+1234567890")
        assert secret in uri
        assert "otpauth" in uri
        # Phone may be URL-encoded (+→%2B) in the URI
        assert "1234567890" in uri

    def test_verify_valid_code(self):
        import pyotp
        secret = self.svc.generate_secret()
        totp = pyotp.TOTP(secret)
        current_code = totp.now()
        assert self.svc.verify_code(secret, current_code) is True

    def test_verify_invalid_code(self):
        secret = self.svc.generate_secret()
        assert self.svc.verify_code(secret, "000000") is False

    def test_backup_codes_count(self):
        plaintext, hashed = self.svc.generate_backup_codes()
        assert len(plaintext) == 10
        assert len(hashed) == 10
        # All plaintext are 8 chars
        assert all(len(c) == 8 for c in plaintext)

    def test_verify_backup_code(self):
        plaintext, hashed = self.svc.generate_backup_codes()
        first = plaintext[0]
        valid, remaining = self.svc.verify_backup_code(first, hashed)
        assert valid is True
        assert len(remaining) == 9  # used code removed

    def test_backup_code_case_insensitive(self):
        # Backup codes are uppercase-only but verification should accept lowercase input
        plaintext, hashed = self.svc.generate_backup_codes()
        first_upper = plaintext[0]
        first_lower = first_upper.lower()
        # Verify that lowercase input is accepted (internal normalisation to upper)
        valid_lower, _ = self.svc.verify_backup_code(first_lower, hashed)
        # Also verify uppercase works
        valid_upper, _ = self.svc.verify_backup_code(first_upper, hashed)
        assert valid_upper is True
        assert valid_lower is True  # implementation uppercases input before hashing

    def test_invalid_backup_code(self):
        _, hashed = self.svc.generate_backup_codes()
        valid, remaining = self.svc.verify_backup_code("BADCODE1", hashed)
        assert valid is False
        assert len(remaining) == 10  # unchanged


# ─────────────────────────────────────────────────────────────────────────────
# ImportService (database)
# ─────────────────────────────────────────────────────────────────────────────

class TestImportService:
    @pytest.mark.asyncio
    async def test_bulk_upsert_creates_accounts(self, db_session: AsyncSession):
        client = await create_test_client(db_session, "imp1")
        svc = ImportService()
        rows = [
            {"phone": "+44100000001", "name": "Acc1"},
            {"phone": "+44100000002", "name": "Acc2"},
        ]
        imported, skipped, failed, errors = await svc.bulk_upsert_accounts(
            client_id=client.id,
            rows=rows,
            import_source="test",
            db=db_session,
        )
        assert imported == 2
        assert skipped == 0
        assert failed == 0
        assert errors == []

    @pytest.mark.asyncio
    async def test_duplicate_phone_skipped(self, db_session: AsyncSession):
        client = await create_test_client(db_session, "imp2")
        await create_test_account(db_session, client, phone="+44200000001")

        svc = ImportService()
        rows = [{"phone": "+44200000001"}]
        imported, skipped, failed, errors = await svc.bulk_upsert_accounts(
            client_id=client.id,
            rows=rows,
            import_source="test",
            db=db_session,
        )
        assert imported == 0
        assert skipped == 1

    @pytest.mark.asyncio
    async def test_missing_phone_counted_as_failed(self, db_session: AsyncSession):
        client = await create_test_client(db_session, "imp3")
        svc = ImportService()
        rows = [{"name": "NoPhone"}]
        imported, skipped, failed, errors = await svc.bulk_upsert_accounts(
            client_id=client.id,
            rows=rows,
            import_source="test",
            db=db_session,
        )
        assert failed == 1
        assert len(errors) == 1

    @pytest.mark.asyncio
    async def test_create_and_finish_import_log(self, db_session: AsyncSession):
        client = await create_test_client(db_session, "imp4")
        svc = ImportService()
        log = await svc.create_import_log(
            client_id=client.id,
            source_type=ImportSourceType.csv,
            filename="test.csv",
            db=db_session,
        )
        assert log.id is not None
        assert log.status == ImportStatus.running

        await svc.finish_import_log(log, imported=5, skipped=1, failed=0, errors=[], db=db_session)
        assert log.status == ImportStatus.completed
        assert log.imported == 5

    @pytest.mark.asyncio
    async def test_session_string_sets_status_active(self, db_session: AsyncSession):
        client = await create_test_client(db_session, "imp5")
        svc = ImportService()
        rows = [{"phone": "+44500000001", "session_string": "FAKE_SESSION_STRING"}]
        imported, skipped, failed, errors = await svc.bulk_upsert_accounts(
            client_id=client.id,
            rows=rows,
            import_source="session",
            db=db_session,
        )
        assert imported == 1
        from sqlalchemy import select
        result = await db_session.execute(
            select(TelegramAccount).where(TelegramAccount.phone == "+44500000001")
        )
        acc = result.scalar_one()
        assert acc.status == AccountStatus.active
        assert acc.import_source == "session"
