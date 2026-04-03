import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class TelegramService:
    """
    Wraps a Telethon client for a single Telegram account.
    Handles login, message sending, group joining, and member scraping.
    """

    def __init__(self, account: Any):
        self.account = account
        self._client: Optional[Any] = None

    async def _get_client(self) -> Any:
        if self._client and self._client.is_connected():
            return self._client
        self._client = await self.connect()
        return self._client

    async def connect(self) -> Optional[Any]:
        """Create and connect a TelethonClient from stored session data."""
        try:
            from telethon import TelegramClient
            from telethon.sessions import StringSession

            api_id = self.account.api_id
            api_hash = self.account.api_hash

            if not api_id or not api_hash:
                from app.config import settings

                api_id = settings.TELEGRAM_API_ID
                api_hash = settings.TELEGRAM_API_HASH

            session = StringSession(self.account.session_data or "")
            client = TelegramClient(session, int(api_id), api_hash)
            await client.connect()
            self._client = client
            return client
        except Exception as exc:
            logger.error(
                "Failed to connect account %s: %s",
                getattr(self.account, "phone", "unknown"),
                exc,
            )
            return None

    async def send_message(self, group: Any, message: Any) -> bool:
        """Send a message to a group. Supports text and media."""
        client = await self._get_client()
        if client is None:
            raise ConnectionError(
                f"Cannot connect account {getattr(self.account, 'phone', 'unknown')}"
            )
        group_id = getattr(group, "group_id", group)
        msg_text = getattr(message, "message_text", str(message))
        media_path = getattr(message, "media_path", None)
        msg_type = getattr(message, "message_type", "text")

        if msg_type in ("photo", "video", "document") and media_path:
            await client.send_file(group_id, media_path, caption=msg_text)
        else:
            await client.send_message(group_id, msg_text)

        logger.debug(
            "Message sent to group %s via account %s",
            group_id,
            getattr(self.account, "phone", "unknown"),
        )
        return True

    async def join_group(self, link_or_username: str) -> Optional[Any]:
        """Join a group by invite link or username and return the entity."""
        client = await self._get_client()
        if client is None:
            raise ConnectionError("Cannot connect Telegram client")
        from telethon.tl.functions.channels import JoinChannelRequest
        from telethon.tl.functions.messages import ImportChatInviteRequest

        if "t.me/joinchat/" in link_or_username or "t.me/+" in link_or_username:
            hash_part = link_or_username.split("/")[-1].lstrip("+")
            result = await client(ImportChatInviteRequest(hash_part))
            return result.chats[0] if result.chats else None
        else:
            username = link_or_username.lstrip("@").replace("https://t.me/", "")
            entity = await client.get_entity(username)
            await client(JoinChannelRequest(entity))
            return entity

    async def get_participants(
        self, group_id: Any, limit: int = 200
    ) -> List[Dict[str, Any]]:
        """Scrape members from a group."""
        client = await self._get_client()
        if client is None:
            raise ConnectionError("Cannot connect Telegram client")
        from telethon.tl.types import UserStatusEmpty

        participants = await client.get_participants(group_id, limit=limit)
        result = []
        for user in participants:
            if user.bot:
                continue
            result.append(
                {
                    "user_id": user.id,
                    "username": user.username,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "phone": getattr(user, "phone", None),
                    "is_bot": user.bot,
                }
            )
        return result

    async def get_me(self) -> Optional[Any]:
        client = await self._get_client()
        if client is None:
            return None
        return await client.get_me()

    async def disconnect(self) -> None:
        if self._client:
            try:
                await self._client.disconnect()
            except Exception:
                pass
            self._client = None
