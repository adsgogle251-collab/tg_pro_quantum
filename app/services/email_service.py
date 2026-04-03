import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import List, Optional

from app.config import settings

logger = logging.getLogger(__name__)


class EmailService:
    """
    Sends email notifications for campaign events and account status changes
    using SMTP (supports TLS).
    """

    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        from_address: Optional[str] = None,
    ):
        self.host = host or settings.SMTP_HOST
        self.port = port or settings.SMTP_PORT
        self.username = username or settings.SMTP_USER
        self.password = password or settings.SMTP_PASSWORD
        self.from_address = from_address or settings.EMAILS_FROM

    def _build_message(
        self, to: List[str], subject: str, body_html: str, body_text: str = ""
    ) -> MIMEMultipart:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = self.from_address
        msg["To"] = ", ".join(to)
        if body_text:
            msg.attach(MIMEText(body_text, "plain"))
        msg.attach(MIMEText(body_html, "html"))
        return msg

    def _send(self, to: List[str], msg: MIMEMultipart) -> None:
        if not self.username or not self.password:
            logger.warning("SMTP credentials not configured; email not sent")
            return
        with smtplib.SMTP(self.host, self.port) as server:
            server.ehlo()
            server.starttls()
            server.login(self.username, self.password)
            server.sendmail(self.from_address, to, msg.as_string())
            logger.info("Email sent to %s: %s", to, msg["Subject"])

    def send_campaign_started(self, to: List[str], campaign_name: str, campaign_id: int) -> None:
        subject = f"[TG Pro Quantum] Campaign '{campaign_name}' started"
        html = f"""
        <h2>Campaign Started</h2>
        <p>Your campaign <strong>{campaign_name}</strong> (ID: {campaign_id}) has started broadcasting.</p>
        <p>You can monitor progress in your dashboard.</p>
        """
        self._send(to, self._build_message(to, subject, html))

    def send_campaign_completed(
        self,
        to: List[str],
        campaign_name: str,
        campaign_id: int,
        sent: int,
        failed: int,
        delivery_rate: float,
    ) -> None:
        subject = f"[TG Pro Quantum] Campaign '{campaign_name}' completed"
        html = f"""
        <h2>Campaign Completed</h2>
        <p>Campaign <strong>{campaign_name}</strong> (ID: {campaign_id}) has finished.</p>
        <ul>
          <li>Messages sent: {sent}</li>
          <li>Messages failed: {failed}</li>
          <li>Delivery rate: {delivery_rate:.1f}%</li>
        </ul>
        """
        self._send(to, self._build_message(to, subject, html))

    def send_account_banned(self, to: List[str], phone: str, account_id: int) -> None:
        subject = "[TG Pro Quantum] Telegram account banned"
        html = f"""
        <h2>Account Banned</h2>
        <p>Account <strong>{phone}</strong> (ID: {account_id}) has been banned by Telegram.</p>
        <p>Please review and replace this account to continue broadcasting.</p>
        """
        self._send(to, self._build_message(to, subject, html))

    def send_campaign_failed(
        self, to: List[str], campaign_name: str, campaign_id: int, reason: str
    ) -> None:
        subject = f"[TG Pro Quantum] Campaign '{campaign_name}' failed"
        html = f"""
        <h2>Campaign Failed</h2>
        <p>Campaign <strong>{campaign_name}</strong> (ID: {campaign_id}) encountered an error.</p>
        <p>Reason: {reason}</p>
        """
        self._send(to, self._build_message(to, subject, html))

    def send_welcome(self, to: List[str], full_name: str) -> None:
        subject = "[TG Pro Quantum] Welcome!"
        html = f"""
        <h2>Welcome to TG Pro Quantum, {full_name}!</h2>
        <p>Your account has been created. Start by creating a client and adding Telegram accounts.</p>
        """
        self._send(to, self._build_message(to, subject, html))
