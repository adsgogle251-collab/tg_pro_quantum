"""
TG PRO QUANTUM - SMS Activate Service
Integrates with SMS Activate API for OTP phone verification.
"""
import asyncio
from typing import Dict, Optional

import aiohttp

from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

BASE_URL = settings.SMS_ACTIVATE_BASE_URL


class SMSActivateService:
    """Async client for SMS Activate API."""

    def __init__(self):
        self._api_key = settings.SMS_ACTIVATE_API_KEY

    async def _request(self, params: dict) -> str:
        """Make a GET request to SMS Activate and return raw text response."""
        params["api_key"] = self._api_key
        async with aiohttp.ClientSession() as session:
            async with session.get(BASE_URL, params=params, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                text = await resp.text()
                logger.debug("SMS Activate response: %s", text)
                return text

    async def request_number(self, phone: Optional[str] = None, country: str = "0", service: str = "tg") -> Dict:
        """
        Request a virtual number for receiving an SMS.
        Returns dict with activation_id and phone_number.
        """
        text = await self._request({"action": "getNumber", "service": service, "country": country})
        # Expected response format: ACCESS_NUMBER:ID:PHONE
        if text.startswith("ACCESS_NUMBER"):
            _, activation_id, phone_number = text.split(":")
            return {"activation_id": activation_id, "phone_number": phone_number}
        raise RuntimeError(f"SMS Activate error: {text}")

    async def get_sms_code(self, activation_id: str, max_wait: int = 60) -> Optional[str]:
        """
        Poll SMS Activate for the received SMS code.
        Waits up to max_wait seconds.
        """
        for _ in range(max_wait // 5):
            text = await self._request({"action": "getStatus", "id": activation_id})
            if text.startswith("STATUS_OK"):
                code = text.split(":")[1]
                return code
            if text in ("STATUS_CANCEL", "STATUS_WAIT_CODE"):
                if text == "STATUS_CANCEL":
                    return None
            await asyncio.sleep(5)
        return None

    async def cancel_activation(self, activation_id: str) -> bool:
        """Cancel an activation that did not receive a code."""
        text = await self._request({"action": "setStatus", "id": activation_id, "status": "8"})
        return text == "ACCESS_CANCEL"

    async def get_balance(self) -> float:
        """Return current account balance."""
        text = await self._request({"action": "getBalance"})
        if text.startswith("ACCESS_BALANCE"):
            return float(text.split(":")[1])
        return 0.0


sms_activate_service = SMSActivateService()
