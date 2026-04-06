"""
core/session_manager.py - 4 import methods for Telegram sessions
"""
import shutil
import re
from pathlib import Path
from typing import Callable, Optional
import asyncio
from datetime import datetime

from telethon import TelegramClient
from telethon.errors import FloodWaitError

from core.config import SESSIONS_DIR, get_api_id, get_api_hash
from core.account import _upsert_account, get_account, _session_path, list_accounts

PHONE_RE = re.compile(r"^\+?\d{7,15}$")


def _extract_phone_from_session(session_path: Path) -> Optional[str]:
    """Try to extract phone number from session filename."""
    name = session_path.stem
    name = name.replace(".session", "")
    clean = name.replace("+", "").replace(" ", "").replace("-", "")
    if clean.isdigit() and 7 <= len(clean) <= 15:
        return f"+{clean}"
    return None


async def _validate_session(
    session_file: Path, api_id: int, api_hash: str
) -> tuple[bool, str, str]:
    """Validate a session file. Returns (valid, phone, name)."""
    session_str = str(session_file).replace(".session", "")
    client = TelegramClient(session_str, api_id, api_hash)
    try:
        await client.connect()
        if not await client.is_user_authorized():
            await client.disconnect()
            return False, "", ""
        me = await client.get_me()
        phone = me.phone or _extract_phone_from_session(session_file) or session_file.stem
        name = me.first_name or phone
        await client.disconnect()
        return True, phone, name
    except Exception:
        try:
            await client.disconnect()
        except Exception:
            pass
        return False, "", ""


def import_single_session(
    source_path: str,
    on_progress: Optional[Callable[[str], None]] = None,
) -> tuple[bool, str]:
    """
    Method 1: Import a single .session file.
    Validates it, extracts name/phone, copies to sessions dir.
    Returns (success, message).
    """
    src = Path(source_path)
    if not src.exists():
        return False, f"File not found: {source_path}"
    if src.suffix != ".session":
        return False, "File must be a .session file"

    api_id = get_api_id()
    api_hash = get_api_hash()

    phone = _extract_phone_from_session(src)
    name = src.stem

    if api_id and api_hash:
        if on_progress:
            on_progress(f"Validating {src.name}...")
        loop = asyncio.new_event_loop()
        try:
            valid, ph, nm = loop.run_until_complete(
                _validate_session(src, api_id, api_hash)
            )
            if valid:
                phone = ph or phone
                name = nm or name
        except Exception:
            pass
        finally:
            loop.close()

    if not phone:
        phone = src.stem

    dest = SESSIONS_DIR / f"{phone.replace('+', '')}.session"
    try:
        shutil.copy2(src, dest)
    except Exception as e:
        return False, f"Copy failed: {e}"

    _upsert_account(
        name,
        phone if phone.startswith("+") else f"+{phone}",
        str(dest),
        "active",
    )

    if on_progress:
        on_progress(f"Imported: {name} ({phone})")
    return True, f"Imported session: {name}"


def import_folder_sessions(
    folder_path: str,
    on_progress: Optional[Callable[[int, int, str], None]] = None,
) -> tuple[int, int, list[str]]:
    """
    Method 2: Import all .session files from a folder.
    Returns (success_count, fail_count, messages).
    """
    folder = Path(folder_path)
    if not folder.is_dir():
        return 0, 0, ["Folder not found"]

    session_files = list(folder.rglob("*.session"))
    if not session_files:
        return 0, 0, ["No .session files found in folder"]

    api_id = get_api_id()
    api_hash = get_api_hash()
    success = 0
    fail = 0
    messages: list[str] = []

    for i, sf in enumerate(session_files):
        if on_progress:
            on_progress(i + 1, len(session_files), f"Processing {sf.name}...")

        phone = _extract_phone_from_session(sf)
        name = sf.stem
        valid = False

        if api_id and api_hash:
            loop = asyncio.new_event_loop()
            try:
                v, ph, nm = loop.run_until_complete(
                    _validate_session(sf, api_id, api_hash)
                )
                if v:
                    valid = True
                    phone = ph or phone
                    name = nm or name
            except Exception:
                pass
            finally:
                loop.close()
        else:
            valid = True

        if not valid and api_id and api_hash:
            fail += 1
            messages.append(f"❌ {sf.name}: Invalid/expired session")
            continue

        if not phone:
            phone = sf.stem

        dest = SESSIONS_DIR / f"{phone.replace('+', '')}.session"
        try:
            shutil.copy2(sf, dest)
            _upsert_account(
                name,
                phone if phone.startswith("+") else f"+{phone}",
                str(dest),
                "active",
            )
            success += 1
            messages.append(f"✅ {sf.name}: Imported as {name}")
        except Exception as e:
            fail += 1
            messages.append(f"❌ {sf.name}: {e}")

    return success, fail, messages


def parse_phone_list(text: str) -> list[str]:
    """
    Parse a text block of phone numbers (one per line).
    Returns list of normalized phone numbers.
    """
    phones: list[str] = []
    for line in text.strip().splitlines():
        line = line.strip()
        if not line:
            continue
        token = line.split()[0]
        phone = re.sub(r"[^\d+]", "", token)
        if not phone.startswith("+"):
            phone = f"+{phone}"
        if PHONE_RE.match(phone):
            phones.append(phone)
    return phones


def import_phones_txt(
    file_path: str,
    on_progress: Optional[Callable[[int, int, str], None]] = None,
) -> tuple[int, list[str]]:
    """
    Method 3: Import phones from TXT file.
    Creates placeholder DB entries (no session yet, status='pending_otp').
    Returns (count, phones_list).
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            text = f.read()
    except Exception:
        return 0, []

    phones = parse_phone_list(text)
    added: list[str] = []
    for i, phone in enumerate(phones):
        if on_progress:
            on_progress(i + 1, len(phones), f"Adding {phone}...")
        if not get_account(phone):
            _upsert_account(phone, phone, "", "pending_otp")
            added.append(phone)

    return len(added), added


def add_phones_manual(
    phones_text: str,
    on_progress: Optional[Callable[[int, int, str], None]] = None,
) -> tuple[int, list[str]]:
    """
    Method 4: Add phones manually (from text input).
    Creates placeholder entries status='pending_otp'.
    Returns (count, phones_list).
    """
    phones = parse_phone_list(phones_text)
    added: list[str] = []
    for i, phone in enumerate(phones):
        if on_progress:
            on_progress(i + 1, len(phones), f"Adding {phone}...")
        if not get_account(phone):
            _upsert_account(phone, phone, "", "pending_otp")
            added.append(phone)
    return len(added), added


session_manager_instance = None  # for compatibility

__all__ = [
    "import_single_session",
    "import_folder_sessions",
    "parse_phone_list",
    "import_phones_txt",
    "add_phones_manual",
]
