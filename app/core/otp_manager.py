"""
TG PRO QUANTUM - OTP Manager (SMS Activate integration)
"""
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.database import OTPStatus, OTPVerification
from app.services.sms_activate_service import sms_activate_service
from app.utils.helpers import generate_otp
from app.utils.logger import get_logger

logger = get_logger(__name__)


class OTPManager:
    """Manages OTP request/verify lifecycle using SMS Activate as the SMS provider."""

    async def request_otp(self, phone: str, db: AsyncSession) -> int:
        """
        Request an OTP for the given phone number.
        Returns the OTPVerification.id for tracking.
        """
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.OTP_EXPIRE_MINUTES)

        # Try SMS Activate first; fall back to a locally-generated code (dev mode)
        sms_id: Optional[str] = None
        otp_code: Optional[str] = None

        if settings.SMS_ACTIVATE_API_KEY:
            try:
                result = await sms_activate_service.request_number(phone)
                sms_id = result.get("activation_id")
                otp_code = result.get("otp_code")  # some providers return code immediately
            except Exception as exc:
                logger.warning("SMS Activate failed for %s: %s", phone, exc)

        if not otp_code:
            otp_code = generate_otp(6)
            logger.debug("Generated local OTP for %s: %s", phone, otp_code)

        otp = OTPVerification(
            phone=phone,
            otp_code=otp_code,
            sms_activate_id=sms_id,
            expires_at=expires_at,
        )
        db.add(otp)
        await db.flush()
        await db.refresh(otp)
        logger.info("OTP created id=%s phone=%s", otp.id, phone)
        return otp.id

    async def verify_otp(self, phone: str, code: str, db: AsyncSession) -> bool:
        """
        Verify the OTP code for the given phone.
        Returns True on success, False on failure/expiry.
        """
        now = datetime.now(timezone.utc)
        result = await db.execute(
            select(OTPVerification)
            .where(
                OTPVerification.phone == phone,
                OTPVerification.status == OTPStatus.pending,
                OTPVerification.expires_at > now,
            )
            .order_by(OTPVerification.created_at.desc())
            .limit(1)
        )
        otp = result.scalar_one_or_none()

        if not otp:
            logger.warning("No active OTP for phone=%s", phone)
            return False

        otp.attempts += 1

        if otp.attempts > settings.OTP_MAX_ATTEMPTS:
            otp.status = OTPStatus.failed
            await db.flush()
            logger.warning("OTP max attempts exceeded for phone=%s", phone)
            return False

        if otp.otp_code != code:
            await db.flush()
            logger.warning("OTP mismatch for phone=%s attempt=%s", phone, otp.attempts)
            return False

        otp.status = OTPStatus.verified
        otp.verified_at = now
        await db.flush()
        logger.info("OTP verified for phone=%s", phone)
        return True

    async def get_sms_code(self, phone: str, db: AsyncSession) -> Optional[str]:
        """
        Poll SMS Activate to retrieve the incoming OTP code (for Telegram login flow).
        Updates the pending OTPVerification record.
        """
        if not settings.SMS_ACTIVATE_API_KEY:
            return None

        result = await db.execute(
            select(OTPVerification)
            .where(OTPVerification.phone == phone, OTPVerification.status == OTPStatus.pending)
            .order_by(OTPVerification.created_at.desc())
            .limit(1)
        )
        otp = result.scalar_one_or_none()
        if not otp or not otp.sms_activate_id:
            return None

        try:
            code = await sms_activate_service.get_sms_code(otp.sms_activate_id)
            if code:
                otp.otp_code = code
                await db.flush()
                return code
        except Exception as exc:
            logger.warning("Failed to poll SMS code for %s: %s", phone, exc)

        return None


otp_manager = OTPManager()
