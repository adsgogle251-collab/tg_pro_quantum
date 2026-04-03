import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

import aiohttp

from app.config import settings

logger = logging.getLogger(__name__)

SMS_STATUS_WAIT_CODE = "STATUS_WAIT_CODE"
SMS_STATUS_OK = "STATUS_OK:"
SMS_STATUS_CANCEL = "STATUS_CANCEL"
SMS_STATUS_TIMEOUT = "STATUS_WAIT_RESEND"

OTP_POLL_INTERVAL = 5  # seconds
OTP_TIMEOUT = 600       # 10 minutes


class OTPManager:
    """
    Manages phone number activation and OTP retrieval via SMS Activate API.
    """

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        self.api_key = api_key or settings.SMS_ACTIVATE_API_KEY
        self.base_url = base_url or settings.SMS_ACTIVATE_BASE_URL

    async def _request(self, params: dict) -> str:
        params["api_key"] = self.api_key
        async with aiohttp.ClientSession() as session:
            async with session.get(self.base_url, params=params) as resp:
                resp.raise_for_status()
                return await resp.text()

    async def get_balance(self) -> float:
        response = await self._request({"action": "getBalance"})
        if response.startswith("ACCESS_BALANCE:"):
            return float(response.split(":")[1])
        raise RuntimeError(f"Unexpected balance response: {response}")

    async def request_number(
        self, phone: Optional[str] = None, service: str = "tg", country: str = "0"
    ) -> str:
        """Request a phone number for activation. Returns activation_id."""
        response = await self._request(
            {
                "action": "getNumber",
                "service": service,
                "country": country,
            }
        )
        if response.startswith("ACCESS_NUMBER:"):
            _, activation_id, _ = response.split(":")
            return activation_id
        if response == "NO_NUMBERS":
            raise RuntimeError("No numbers available for the selected country/service")
        if response == "NO_BALANCE":
            raise RuntimeError("Insufficient balance on SMS Activate account")
        raise RuntimeError(f"getNumber failed: {response}")

    async def get_otp_code(self, activation_id: str, timeout: int = OTP_TIMEOUT) -> str:
        """Poll for OTP code until received or timeout."""
        deadline = datetime.now(timezone.utc) + timedelta(seconds=timeout)
        while datetime.now(timezone.utc) < deadline:
            response = await self._request(
                {
                    "action": "getStatus",
                    "id": activation_id,
                }
            )
            if response.startswith(SMS_STATUS_OK):
                code = response[len(SMS_STATUS_OK):]
                logger.info("OTP received for activation %s: %s", activation_id, code)
                await self.set_status(activation_id, 6)  # mark as used
                return code
            if response == SMS_STATUS_CANCEL:
                raise RuntimeError(f"Activation {activation_id} was cancelled")
            if response == SMS_STATUS_TIMEOUT:
                await self.set_status(activation_id, 3)  # request resend
            # STATUS_WAIT_CODE or STATUS_WAIT_RESEND - keep polling
            await asyncio.sleep(OTP_POLL_INTERVAL)

        await self.cancel_activation(activation_id)
        raise TimeoutError(f"OTP not received within {timeout} seconds")

    async def set_status(self, activation_id: str, status_code: int) -> str:
        """
        Set activation status:
          1 = SMS ready to receive
          3 = Resend SMS
          6 = Confirm SMS code
          8 = Cancel activation
        """
        response = await self._request(
            {
                "action": "setStatus",
                "id": activation_id,
                "status": status_code,
            }
        )
        return response

    async def cancel_activation(self, activation_id: str) -> None:
        await self.set_status(activation_id, 8)
        logger.info("Activation %s cancelled", activation_id)

    async def verify_otp(self, activation_id: str, otp_code: str) -> bool:
        """Confirm that the OTP code is valid and mark activation complete."""
        response = await self._request(
            {
                "action": "getStatus",
                "id": activation_id,
            }
        )
        if response.startswith(SMS_STATUS_OK):
            received_code = response[len(SMS_STATUS_OK):]
            if received_code == otp_code:
                await self.set_status(activation_id, 6)
                return True
        return False
