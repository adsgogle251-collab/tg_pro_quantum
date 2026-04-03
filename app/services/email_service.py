"""
TG PRO QUANTUM - Email Notification Service
"""
import asyncio
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


class EmailService:
    """Sends transactional emails via SMTP."""

    async def send_email(
        self,
        to: str,
        subject: str,
        body_html: str,
        body_text: Optional[str] = None,
    ) -> bool:
        """Send an email. Returns True on success."""
        if not settings.SMTP_HOST:
            logger.debug("SMTP not configured – skipping email to %s", to)
            return False

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = settings.EMAIL_FROM
        msg["To"] = to

        if body_text:
            msg.attach(MIMEText(body_text, "plain"))
        msg.attach(MIMEText(body_html, "html"))

        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._smtp_send, to, msg)
            logger.info("Email sent to %s: %s", to, subject)
            return True
        except Exception as exc:
            logger.error("Failed to send email to %s: %s", to, exc)
            return False

    def _smtp_send(self, to: str, msg: MIMEMultipart) -> None:
        import ssl
        context = ssl.create_default_context()
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            server.ehlo()
            server.starttls(context=context)
            if settings.SMTP_USER and settings.SMTP_PASSWORD:
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.sendmail(settings.EMAIL_FROM, to, msg.as_string())

    async def send_campaign_complete(self, to: str, campaign_name: str, sent: int, failed: int) -> bool:
        subject = f"[TG PRO QUANTUM] Campaign '{campaign_name}' completed"
        html = f"""
        <h2>Campaign Complete</h2>
        <p>Your campaign <strong>{campaign_name}</strong> has finished.</p>
        <ul>
          <li>✅ Sent: {sent}</li>
          <li>❌ Failed: {failed}</li>
          <li>📊 Delivery rate: {round(sent / max(sent + failed, 1) * 100, 1)}%</li>
        </ul>
        """
        return await self.send_email(to, subject, html)


email_service = EmailService()
