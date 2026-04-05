"""
TG PRO QUANTUM - Account Import Service

Handles three import modes:
1. **Session import** – parse a raw Telegram session string (or Ctrl+A pasted text)
   and extract ``phone``, ``api_id``, ``api_hash``, ``session_string``.
2. **CSV / Excel import** – stream a file, validate rows, deduplicate, persist.
3. **Bulk create** – accept a JSON list of account dicts and persist all at once.

Each run is tracked with an :class:`ImportLog` record so the client can poll
progress or inspect past imports.
"""
from __future__ import annotations

import csv
import io
import json
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import (
    AccountStatus,
    ImportLog,
    ImportSourceType,
    ImportStatus,
    TelegramAccount,
)
from app.utils.logger import get_logger

logger = get_logger(__name__)

# ── Session string parsing ────────────────────────────────────────────────────

# A very loose regex to detect Telethon / Pyrogram base64-ish session strings
_SESSION_RE = re.compile(r"[A-Za-z0-9+/=_-]{20,}")

# Patterns for phone numbers
_PHONE_RE = re.compile(r"\+?[1-9]\d{6,14}")

# Required CSV column names (case-insensitive); phone is always required
_CSV_REQUIRED = {"phone"}
_CSV_OPTIONAL = {"name", "api_id", "api_hash", "session_string", "tags"}


def parse_session_text(text: str) -> Dict[str, Any]:
    """
    Parse a pasted Telegram session block (e.g. from Ctrl+A copy).

    Supported formats:
    - ``phone|api_id|api_hash|session_string``  (pipe-delimited)
    - ``phone:api_id:api_hash:session_string``   (colon-delimited)
    - JSON  ``{"phone": ..., "api_id": ..., ...}``
    - Plain session string (only the session; phone must be provided separately)

    Returns a dict with any of: ``phone``, ``api_id``, ``api_hash``,
    ``session_string``.  Missing keys are simply absent.
    """
    text = text.strip()

    # Try JSON first
    if text.startswith("{"):
        try:
            data = json.loads(text)
            return _normalise_parsed(data)
        except json.JSONDecodeError:
            pass

    # Try pipe / colon delimited: phone|api_id|api_hash|session
    for sep in ("|", ":"):
        parts = [p.strip() for p in text.split(sep)]
        if len(parts) >= 4:
            phone_candidate = parts[0]
            if _PHONE_RE.fullmatch(phone_candidate.lstrip("+")):
                return _normalise_parsed({
                    "phone": parts[0],
                    "api_id": parts[1],
                    "api_hash": parts[2],
                    "session_string": sep.join(parts[3:]),
                })

    # Fallback: treat the whole text as a session string
    if _SESSION_RE.fullmatch(text):
        return {"session_string": text}

    return {}


def _normalise_parsed(data: Dict[str, Any]) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    if "phone" in data:
        out["phone"] = str(data["phone"]).strip()
    if "api_id" in data:
        try:
            out["api_id"] = int(data["api_id"])
        except (ValueError, TypeError):
            pass
    if "api_hash" in data:
        out["api_hash"] = str(data["api_hash"]).strip()
    if "session_string" in data:
        out["session_string"] = str(data["session_string"]).strip()
    if "name" in data:
        out["name"] = str(data["name"]).strip()
    return out


# ── CSV parsing ───────────────────────────────────────────────────────────────

def parse_csv_content(content: bytes | str) -> Tuple[List[Dict[str, Any]], List[str]]:
    """
    Parse a CSV file (bytes or str) into a list of account dicts.

    Returns ``(rows, errors)`` where *errors* contains row-level problem strings.
    The ``phone`` column is required; all others are optional.
    """
    if isinstance(content, bytes):
        content = content.decode("utf-8-sig", errors="replace")

    rows: List[Dict[str, Any]] = []
    errors: List[str] = []
    reader = csv.DictReader(io.StringIO(content))

    if reader.fieldnames is None:
        return [], ["CSV file appears to be empty or has no header row"]

    col_map = {c.strip().lower(): c for c in reader.fieldnames}
    if "phone" not in col_map:
        return [], ["CSV must contain a 'phone' column"]

    for i, raw_row in enumerate(reader, start=2):  # 1-indexed, row 1 is header
        normalised: Dict[str, Any] = {}
        phone_raw = raw_row.get(col_map.get("phone", ""), "").strip()
        if not phone_raw:
            errors.append(f"Row {i}: missing phone")
            continue
        normalised["phone"] = phone_raw

        for field in ("name", "api_hash", "session_string"):
            col = col_map.get(field)
            if col and raw_row.get(col, "").strip():
                normalised[field] = raw_row[col].strip()

        api_id_col = col_map.get("api_id")
        if api_id_col and raw_row.get(api_id_col, "").strip():
            try:
                normalised["api_id"] = int(raw_row[api_id_col].strip())
            except ValueError:
                errors.append(f"Row {i}: api_id is not an integer")

        tags_col = col_map.get("tags")
        if tags_col and raw_row.get(tags_col, "").strip():
            normalised["tags"] = [t.strip() for t in raw_row[tags_col].split(",") if t.strip()]

        rows.append(normalised)

    return rows, errors


# ── Excel / XLSX parsing ──────────────────────────────────────────────────────

def parse_excel_content(content: bytes) -> Tuple[List[Dict[str, Any]], List[str]]:
    """
    Parse an Excel (.xlsx) file into account dicts using openpyxl.

    Falls back gracefully if openpyxl is not installed.
    """
    try:
        import openpyxl  # type: ignore
    except ImportError:
        return [], ["openpyxl is not installed; Excel import is unavailable"]

    rows: List[Dict[str, Any]] = []
    errors: List[str] = []

    try:
        wb = openpyxl.load_workbook(io.BytesIO(content), read_only=True, data_only=True)
        ws = wb.active
        sheet_rows = list(ws.iter_rows(values_only=True))
    except Exception as exc:
        return [], [f"Failed to read Excel file: {exc}"]

    if not sheet_rows:
        return [], ["Excel file is empty"]

    header = [str(c).strip().lower() if c is not None else "" for c in sheet_rows[0]]
    if "phone" not in header:
        return [], ["Excel must have a 'phone' column in the first row"]

    col_idx: Dict[str, int] = {name: i for i, name in enumerate(header)}

    for row_num, row in enumerate(sheet_rows[1:], start=2):
        phone_val = row[col_idx["phone"]] if "phone" in col_idx else None
        if not phone_val:
            errors.append(f"Row {row_num}: missing phone")
            continue
        normalised: Dict[str, Any] = {"phone": str(phone_val).strip()}

        for field in ("name", "api_hash", "session_string"):
            idx = col_idx.get(field)
            if idx is not None and row[idx] is not None:
                normalised[field] = str(row[idx]).strip()

        idx = col_idx.get("api_id")
        if idx is not None and row[idx] is not None:
            try:
                normalised["api_id"] = int(row[idx])
            except (ValueError, TypeError):
                errors.append(f"Row {row_num}: api_id is not an integer")

        idx = col_idx.get("tags")
        if idx is not None and row[idx] is not None:
            normalised["tags"] = [t.strip() for t in str(row[idx]).split(",") if t.strip()]

        rows.append(normalised)

    return rows, errors


# ── Database persistence ──────────────────────────────────────────────────────

class ImportService:
    """Coordinates parsing, deduplication, and database persistence of accounts."""

    async def create_import_log(
        self,
        client_id: int,
        source_type: ImportSourceType,
        filename: Optional[str],
        db: AsyncSession,
    ) -> ImportLog:
        log = ImportLog(
            client_id=client_id,
            source_type=source_type,
            status=ImportStatus.running,
            started_at=datetime.now(timezone.utc),
            filename=filename,
        )
        db.add(log)
        await db.flush()
        await db.refresh(log)
        return log

    async def bulk_upsert_accounts(
        self,
        client_id: int,
        rows: List[Dict[str, Any]],
        import_source: str,
        db: AsyncSession,
    ) -> Tuple[int, int, int, List[str]]:
        """
        Insert accounts from *rows*, skipping duplicates (same client + phone).

        Returns ``(imported, skipped, failed, errors)``.
        """
        imported = skipped = failed = 0
        errors: List[str] = []

        # Fetch existing phones for this client in one query
        existing_result = await db.execute(
            select(TelegramAccount.phone).where(TelegramAccount.client_id == client_id)
        )
        existing_phones = {r[0] for r in existing_result.all()}

        for i, row in enumerate(rows):
            phone = row.get("phone", "").strip()
            if not phone:
                errors.append(f"Row {i + 1}: missing phone")
                failed += 1
                continue

            if phone in existing_phones:
                skipped += 1
                continue

            try:
                account = TelegramAccount(
                    client_id=client_id,
                    phone=phone,
                    name=row.get("name") or phone,
                    api_id=row.get("api_id"),
                    api_hash=row.get("api_hash"),
                    session_string=row.get("session_string"),
                    tags=row.get("tags", []),
                    import_source=import_source,
                    last_activity=datetime.now(timezone.utc),
                    status=(
                        AccountStatus.active
                        if row.get("session_string")
                        else AccountStatus.unverified
                    ),
                )
                db.add(account)
                existing_phones.add(phone)
                imported += 1
            except Exception as exc:
                errors.append(f"Row {i + 1} ({phone}): {exc}")
                failed += 1

        return imported, skipped, failed, errors

    async def finish_import_log(
        self,
        log: ImportLog,
        imported: int,
        skipped: int,
        failed: int,
        errors: List[str],
        db: AsyncSession,
    ) -> None:
        log.imported = imported
        log.skipped = skipped
        log.failed_rows = failed
        log.total_rows = imported + skipped + failed
        log.errors = errors[:100]  # cap error list
        log.finished_at = datetime.now(timezone.utc)
        log.status = (
            ImportStatus.completed
            if failed == 0
            else (ImportStatus.partial if imported > 0 else ImportStatus.failed)
        )
        await db.flush()


import_service = ImportService()
