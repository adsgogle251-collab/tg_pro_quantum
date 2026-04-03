import asyncio
import logging
from typing import Optional

import aiohttp

from app.config import settings

logger = logging.getLogger(__name__)

ACTION_GET_NUMBER = "getNumber"
ACTION_GET_STATUS = "getStatus"
ACTION_SET_STATUS = "setStatus"
ACTION_GET_BALANCE = "getBalance"

POLL_INTERVAL = 5
MAX_WAIT = 600


class SMSActivateService:
    """Full SMS Activate API integration for phone number activation."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
    ):
        self.api_key = api_key or settings.SMS_ACTIVATE_API_KEY
        self.base_url = base_url or settings.SMS_ACTIVATE_BASE_URL

    async def _get(self, params: dict) -> str:
        params["api_key"] = self.api_key
        async with aiohttp.ClientSession() as session:
            async with session.get(self.base_url, params=params) as resp:
                resp.raise_for_status()
                return await resp.text()

    async def get_balance(self) -> float:
        resp = await self._get({"action": ACTION_GET_BALANCE})
        if resp.startswith("ACCESS_BALANCE:"):
            return float(resp.split(":")[1])
        raise RuntimeError(f"Balance error: {resp}")

    async def get_number(self, service: str = "tg", country: str = "0") -> dict:
        """
        Request a number for activation.
        Returns {"activation_id": str, "phone_number": str}
        """
        resp = await self._get(
            {
                "action": ACTION_GET_NUMBER,
                "service": service,
                "country": country,
            }
        )
        if resp.startswith("ACCESS_NUMBER:"):
            _, activation_id, phone = resp.split(":")
            return {"activation_id": activation_id, "phone_number": phone}
        if resp == "NO_NUMBERS":
            raise RuntimeError("No numbers available")
        if resp == "NO_BALANCE":
            raise RuntimeError("Insufficient balance")
        raise RuntimeError(f"Unexpected response: {resp}")

    async def get_status(self, activation_id: str) -> str:
        """Return raw status string from SMS Activate."""
        resp = await self._get(
            {
                "action": ACTION_GET_STATUS,
                "id": activation_id,
            }
        )
        return resp

    async def set_status(self, activation_id: str, status: int) -> str:
        """
        Set activation status code.
        1=ready, 3=resend, 6=used, 8=cancel
        """
        resp = await self._get(
            {
                "action": ACTION_SET_STATUS,
                "id": activation_id,
                "status": status,
            }
        )
        return resp

    async def wait_for_code(
        self, activation_id: str, timeout: int = MAX_WAIT
    ) -> str:
        """Poll until an SMS code is received or timeout is reached."""
        elapsed = 0
        while elapsed < timeout:
            status = await self.get_status(activation_id)
            if status.startswith("STATUS_OK:"):
                code = status[len("STATUS_OK:"):]
                await self.set_status(activation_id, 6)  # confirm used
                return code
            if status == "STATUS_CANCEL":
                raise RuntimeError(f"Activation {activation_id} cancelled")
            await asyncio.sleep(POLL_INTERVAL)
            elapsed += POLL_INTERVAL

        await self.cancel_number(activation_id)
        raise TimeoutError(f"No SMS received within {timeout}s")

    async def cancel_number(self, activation_id: str) -> None:
        await self.set_status(activation_id, 8)
        logger.info("Cancelled activation %s", activation_id)

    async def get_countries(self) -> dict:
        """Fetch available countries."""
        resp = await self._get({"action": "getCountries"})
        import json

        try:
            return json.loads(resp)
        except Exception:
            return {}

    async def get_services(self, country: str = "0") -> dict:
        """Fetch available services for a country."""
        resp = await self._get({"action": "getNumbersStatus", "country": country})
        import json

        try:
            return json.loads(resp)
        except Exception:
            return {}
