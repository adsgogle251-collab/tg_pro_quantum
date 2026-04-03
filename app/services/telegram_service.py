"""
TG PRO QUANTUM - Telegram Service Wrapper (async Telethon)
"""
import asyncio
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from app.config import settings
from app.models.database import TelegramAccount
from app.utils.helpers import safe_username
from app.utils.logger import get_logger

logger = get_logger(__name__)


class TelegramService:
    """Thin async wrapper around Telethon for use inside Celery workers & FastAPI."""

    def _get_client(self, account: TelegramAccount):
        """Create a Telethon TelegramClient from account credentials."""
        try:
            from telethon import TelegramClient
            from telethon.sessions import StringSession
        except ImportError:
            raise RuntimeError("telethon is not installed – pip install telethon")

        session = StringSession(account.session_string or "")
        return TelegramClient(
            session,
            account.api_id or settings.TELEGRAM_API_ID,
            account.api_hash or settings.TELEGRAM_API_HASH,
            device_model="TG PRO QUANTUM",
            app_version=settings.APP_VERSION,
        )

    async def test_connection(self, account: TelegramAccount) -> bool:
        """Check if the account session is still valid."""
        client = self._get_client(account)
        try:
            await client.connect()
            return await client.is_user_authorized()
        except Exception as exc:
            logger.debug("test_connection failed for %s: %s", account.phone, exc)
            return False
        finally:
            try:
                await client.disconnect()
            except Exception:
                pass

    async def send_message(
        self,
        account: TelegramAccount,
        username: str,
        text: str,
        media_url: Optional[str] = None,
    ) -> Tuple[bool, Optional[str]]:
        """
        Send a message to a group/channel.
        Returns (success, error_message).
        """
        from telethon import errors

        client = self._get_client(account)
        try:
            await client.connect()
            if not await client.is_user_authorized():
                return False, "Account not authorized"

            target = safe_username(username)
            entity = await client.get_entity(target)

            if media_url:
                await client.send_message(entity, text, file=media_url)
            else:
                await client.send_message(entity, text)

            logger.info("Sent to @%s via account %s", target, account.phone)
            return True, None

        except errors.FloodWaitError as e:
            return False, f"FloodWait: {e.seconds}s"
        except errors.UserBannedInChannelError:
            return False, "User banned in channel"
        except errors.ChatWriteForbiddenError:
            return False, "Write forbidden"
        except Exception as exc:
            logger.error("send_message error for @%s: %s", username, exc)
            return False, str(exc)
        finally:
            try:
                await client.disconnect()
            except Exception:
                pass

    async def join_group(self, account: TelegramAccount, username: str) -> bool:
        """Join a Telegram group/channel."""
        from telethon.tl.functions.channels import JoinChannelRequest
        from telethon import errors

        client = self._get_client(account)
        try:
            await client.connect()
            target = safe_username(username)
            entity = await client.get_entity(target)
            await client(JoinChannelRequest(entity))
            return True
        except errors.UserAlreadyParticipantError:
            return True  # already in group – treat as success
        except Exception as exc:
            logger.error("join_group @%s error: %s", username, exc)
            return False
        finally:
            try:
                await client.disconnect()
            except Exception:
                pass

    async def get_members(
        self,
        account: TelegramAccount,
        username: str,
        limit: int = 200,
    ) -> List[Dict]:
        """Scrape members from a group."""
        from telethon.tl.functions.channels import GetParticipantsRequest
        from telethon.tl.types import ChannelParticipantsSearch

        client = self._get_client(account)
        members = []
        try:
            await client.connect()
            target = safe_username(username)
            entity = await client.get_entity(target)
            result = await client(
                GetParticipantsRequest(entity, ChannelParticipantsSearch(""), 0, limit, 0)
            )
            for user in result.users:
                members.append({
                    "id": user.id,
                    "username": user.username,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "phone": getattr(user, "phone", None),
                })
        except Exception as exc:
            logger.error("get_members @%s error: %s", username, exc)
        finally:
            try:
                await client.disconnect()
            except Exception:
                pass
        return members

    async def get_group_info(self, account: TelegramAccount, username: str) -> Optional[Dict]:
        """Fetch group metadata."""
        client = self._get_client(account)
        try:
            await client.connect()
            target = safe_username(username)
            entity = await client.get_entity(target)
            return {
                "title": getattr(entity, "title", ""),
                "members_count": getattr(entity, "participants_count", 0),
                "id": entity.id,
            }
        except Exception as exc:
            logger.error("get_group_info @%s error: %s", username, exc)
            return None
        finally:
            try:
                await client.disconnect()
            except Exception:
                pass
