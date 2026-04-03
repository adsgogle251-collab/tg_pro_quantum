"""TG PRO QUANTUM - Real Telegram Client (Telethon-based)

This module provides real Telegram API integration for the core layer:
- Phone login with OTP (send_code → sign_in)
- Session file persistence to /sessions/{phone}.session
- Send messages to groups/channels
- Join groups/channels
- Scrape group members
"""
import asyncio
from pathlib import Path
from typing import Optional, List, Dict, Tuple

from .utils import SESSIONS_DIR, log, log_error
from .config_manager import load_config


def _get_api_credentials() -> Tuple[int, str]:
    """Load API ID and hash from config."""
    config = load_config()
    api_id = config.get("telegram", {}).get("api_id", 0)
    api_hash = config.get("telegram", {}).get("api_hash", "")
    return int(api_id), str(api_hash)


def _session_path(phone: str) -> Path:
    """Return the absolute path of the .session file for a phone number."""
    # Normalise phone: strip leading '+' for filename safety but keep digits
    safe = phone.lstrip("+").replace(" ", "")
    return SESSIONS_DIR / f"{safe}.session"


def _make_client(phone: str):
    """Create a TelegramClient using the file-based session for *phone*."""
    try:
        from telethon import TelegramClient as _TC
    except ImportError:
        raise RuntimeError(
            "telethon is not installed – run: pip install telethon"
        )

    api_id, api_hash = _get_api_credentials()
    if not api_id or not api_hash:
        raise RuntimeError(
            "Telegram API ID / Hash not configured. "
            "Go to Settings and enter your api_id and api_hash."
        )

    session_file = _session_path(phone)
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)

    return _TC(
        str(session_file),
        api_id,
        api_hash,
        device_model="TG PRO QUANTUM",
        app_version="7.0.0",
    )


# ── Login / OTP ────────────────────────────────────────────────────────────────

async def request_login_code(phone: str) -> dict:
    """
    Send an OTP to *phone* via Telegram.

    Returns a dict::
        {
            "phone_code_hash": str,   # needed for sign_in
            "type": "app" | "sms",    # where the code was sent
            "timeout": int,           # seconds before timeout
        }
    Raises RuntimeError on failure.
    """
    from telethon import errors

    client = _make_client(phone)
    try:
        await client.connect()

        if await client.is_user_authorized():
            log(f"Phone {phone} is already authorized – no OTP needed", "info")
            return {"already_authorized": True, "phone_code_hash": ""}

        result = await client.send_code_request(phone)
        log(f"OTP sent to {phone} (type={result.type.__class__.__name__})", "info")
        return {
            "already_authorized": False,
            "phone_code_hash": result.phone_code_hash,
            "type": result.type.__class__.__name__,
            "timeout": getattr(result, "timeout", 120),
        }
    except errors.FloodWaitError as e:
        raise RuntimeError(f"Flood wait: please try again in {e.seconds} seconds")
    except errors.PhoneNumberBannedError:
        raise RuntimeError("This phone number is banned from Telegram")
    except errors.PhoneNumberInvalidError:
        raise RuntimeError("Invalid phone number format (use +countrycode format)")
    except Exception as exc:
        raise RuntimeError(f"Failed to send OTP: {exc}") from exc
    finally:
        try:
            await client.disconnect()
        except Exception:
            pass


async def sign_in_with_code(
    phone: str,
    code: str,
    phone_code_hash: str,
    password: str = "",
) -> dict:
    """
    Verify the OTP *code* for *phone* and persist the session.

    *password* is required only if the account has 2FA enabled.

    Returns a dict::
        {
            "success": bool,
            "user": {"first_name": str, "username": str, "id": int},
            "session_file": str,
        }
    """
    from telethon import errors
    from telethon.tl.types import User

    client = _make_client(phone)
    try:
        await client.connect()

        try:
            user = await client.sign_in(phone, code, phone_code_hash=phone_code_hash)
        except errors.SessionPasswordNeededError:
            if not password:
                raise RuntimeError(
                    "2FA is enabled on this account – please provide your password"
                )
            user = await client.sign_in(password=password)

        session_file = _session_path(phone)
        log(f"✅ Signed in as {getattr(user, 'first_name', phone)} – session saved to {session_file}", "success")

        return {
            "success": True,
            "user": {
                "id": user.id if isinstance(user, User) else 0,
                "first_name": getattr(user, "first_name", ""),
                "username": getattr(user, "username", ""),
                "phone": phone,
            },
            "session_file": str(session_file),
        }

    except errors.PhoneCodeExpiredError:
        raise RuntimeError("OTP code has expired – please request a new code")
    except errors.PhoneCodeInvalidError:
        raise RuntimeError("Invalid OTP code – check and try again")
    except errors.PasswordHashInvalidError:
        raise RuntimeError("Incorrect 2FA password")
    except Exception as exc:
        raise RuntimeError(f"Sign-in failed: {exc}") from exc
    finally:
        try:
            await client.disconnect()
        except Exception:
            pass


async def logout(phone: str) -> bool:
    """Log out and delete the session file for *phone*."""
    client = _make_client(phone)
    try:
        await client.connect()
        await client.log_out()
        log(f"Logged out {phone}", "info")
    except Exception as exc:
        log_error(f"Logout error for {phone}: {exc}")
    finally:
        try:
            await client.disconnect()
        except Exception:
            pass

    session_file = _session_path(phone)
    if session_file.exists():
        session_file.unlink()
    return True


async def is_authorized(phone: str) -> bool:
    """Return True if the stored session for *phone* is still valid."""
    session_file = _session_path(phone)
    if not session_file.exists():
        return False
    client = _make_client(phone)
    try:
        await client.connect()
        return await client.is_user_authorized()
    except Exception:
        return False
    finally:
        try:
            await client.disconnect()
        except Exception:
            pass


# ── Messaging ─────────────────────────────────────────────────────────────────

async def send_message(
    phone: str,
    group: str,
    text: str,
    media_path: Optional[str] = None,
) -> Tuple[bool, Optional[str]]:
    """
    Send *text* (optionally with *media_path*) to *group* using *phone*'s session.

    Returns ``(success, error_message)``.
    """
    from telethon import errors

    client = _make_client(phone)
    try:
        await client.connect()

        if not await client.is_user_authorized():
            return False, f"Account {phone} is not authorized – login first"

        target = group.lstrip("@")
        entity = await client.get_entity(target)

        if media_path:
            await client.send_message(entity, text, file=media_path)
        else:
            await client.send_message(entity, text)

        log(f"✅ Sent to @{target} via {phone}", "success")
        return True, None

    except errors.FloodWaitError as e:
        msg = f"FloodWait: retry in {e.seconds}s"
        log_error(msg)
        return False, msg
    except errors.UserBannedInChannelError:
        return False, "Account banned from this channel"
    except errors.ChatWriteForbiddenError:
        return False, "Write permission denied"
    except errors.ChannelPrivateError:
        return False, "Channel is private / account not a member"
    except Exception as exc:
        log_error(f"send_message to {group}: {exc}")
        return False, str(exc)
    finally:
        try:
            await client.disconnect()
        except Exception:
            pass


# ── Join ──────────────────────────────────────────────────────────────────────

async def join_group(phone: str, group: str) -> Tuple[bool, Optional[str]]:
    """
    Join *group* using *phone*'s session.

    Returns ``(success, error_message)``.
    """
    from telethon import errors
    from telethon.tl.functions.channels import JoinChannelRequest
    from telethon.tl.functions.messages import ImportChatInviteRequest

    client = _make_client(phone)
    try:
        await client.connect()

        if not await client.is_user_authorized():
            return False, f"Account {phone} is not authorized – login first"

        # Handle invite links like https://t.me/joinchat/HASH or t.me/+HASH
        invite_hash = None
        if "joinchat/" in group:
            invite_hash = group.split("joinchat/")[-1].strip("/")
        elif group.startswith("+") and "/" not in group:
            invite_hash = group[1:]  # private link hash

        if invite_hash:
            await client(ImportChatInviteRequest(invite_hash))
        else:
            target = group.lstrip("@").split("/")[-1]
            entity = await client.get_entity(target)
            await client(JoinChannelRequest(entity))

        log(f"✅ Joined {group} via {phone}", "success")
        return True, None

    except errors.UserAlreadyParticipantError:
        return True, None  # already a member
    except errors.FloodWaitError as e:
        msg = f"FloodWait: retry in {e.seconds}s"
        return False, msg
    except errors.InviteHashExpiredError:
        return False, "Invite link has expired"
    except errors.ChannelPrivateError:
        return False, "Channel is private"
    except Exception as exc:
        log_error(f"join_group {group}: {exc}")
        return False, str(exc)
    finally:
        try:
            await client.disconnect()
        except Exception:
            pass


# ── Scrape ────────────────────────────────────────────────────────────────────

async def scrape_members(
    phone: str,
    group: str,
    limit: int = 200,
) -> List[Dict]:
    """
    Scrape up to *limit* members from *group* using *phone*'s session.

    Returns a list of member dicts with keys: id, username, first_name, last_name, phone.
    """
    from telethon import errors
    from telethon.tl.functions.channels import GetParticipantsRequest
    from telethon.tl.types import ChannelParticipantsSearch

    client = _make_client(phone)
    members: List[Dict] = []

    try:
        await client.connect()

        if not await client.is_user_authorized():
            log_error(f"Account {phone} not authorized for scraping")
            return []

        target = group.lstrip("@")
        entity = await client.get_entity(target)

        offset = 0
        chunk = min(limit, 200)

        while len(members) < limit:
            result = await client(
                GetParticipantsRequest(
                    entity,
                    ChannelParticipantsSearch(""),
                    offset=offset,
                    limit=chunk,
                    hash=0,
                )
            )
            if not result.users:
                break

            for user in result.users:
                members.append({
                    "id": user.id,
                    "username": user.username or "",
                    "first_name": user.first_name or "",
                    "last_name": user.last_name or "",
                    "phone": getattr(user, "phone", "") or "",
                })

            offset += len(result.users)
            if len(result.users) < chunk:
                break

            await asyncio.sleep(1)  # rate-limit scraping

        log(f"📥 Scraped {len(members)} members from {group}", "success")
        return members

    except errors.ChatAdminRequiredError:
        log_error(f"Admin required to scrape {group}")
        return []
    except errors.ChannelPrivateError:
        log_error(f"Cannot scrape private channel {group}")
        return []
    except Exception as exc:
        log_error(f"scrape_members {group}: {exc}")
        return []
    finally:
        try:
            await client.disconnect()
        except Exception:
            pass


# ── Group info ────────────────────────────────────────────────────────────────

async def get_group_info(phone: str, group: str) -> Optional[Dict]:
    """Fetch basic info about *group* using *phone*'s session."""
    client = _make_client(phone)
    try:
        await client.connect()
        if not await client.is_user_authorized():
            return None
        target = group.lstrip("@")
        entity = await client.get_entity(target)
        return {
            "id": entity.id,
            "title": getattr(entity, "title", ""),
            "username": getattr(entity, "username", ""),
            "members_count": getattr(entity, "participants_count", 0),
        }
    except Exception as exc:
        log_error(f"get_group_info {group}: {exc}")
        return None
    finally:
        try:
            await client.disconnect()
        except Exception:
            pass


# ── Convenience: run async from sync context ──────────────────────────────────

def run_async(coro):
    """Run *coro* in the current or a new event loop."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(asyncio.run, coro)
                return future.result()
        else:
            return loop.run_until_complete(coro)
    except RuntimeError:
        return asyncio.run(coro)


__all__ = [
    "request_login_code",
    "sign_in_with_code",
    "logout",
    "is_authorized",
    "send_message",
    "join_group",
    "scrape_members",
    "get_group_info",
    "run_async",
]
