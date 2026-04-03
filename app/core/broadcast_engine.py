import asyncio
import logging
import random
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class BroadcastEngine:
    """
    Multi-account broadcast engine with smart anti-ban delays,
    round-robin account rotation, retry logic, and loop mode.
    """

    def __init__(self):
        self._running: Dict[int, bool] = {}
        self._paused: Dict[int, bool] = {}
        self._progress: Dict[int, Dict[str, Any]] = {}

    def is_running(self, campaign_id: int) -> bool:
        return self._running.get(campaign_id, False)

    def is_paused(self, campaign_id: int) -> bool:
        return self._paused.get(campaign_id, False)

    def stop(self, campaign_id: int) -> None:
        self._running[campaign_id] = False

    def pause(self, campaign_id: int) -> None:
        self._paused[campaign_id] = True

    def resume(self, campaign_id: int) -> None:
        self._paused[campaign_id] = False

    def get_progress(self, campaign_id: int) -> Dict[str, Any]:
        return self._progress.get(campaign_id, {})

    async def run_campaign(
        self,
        campaign_id: int,
        accounts: List[Any],
        groups: List[Any],
        messages: List[Any],
        delay_min: int = 5,
        delay_max: int = 15,
        max_messages_per_hour: int = 100,
        loop_count: int = 0,
        is_loop_infinite: bool = False,
        on_progress: Optional[Callable] = None,
        on_message_sent: Optional[Callable] = None,
        on_message_failed: Optional[Callable] = None,
    ) -> Dict[str, Any]:
        self._running[campaign_id] = True
        self._paused[campaign_id] = False
        self._progress[campaign_id] = {
            "sent": 0,
            "failed": 0,
            "total": len(groups) * len(messages),
            "started_at": datetime.utcnow().isoformat(),
        }

        active_accounts = [a for a in accounts if getattr(a, "status", None) == "active"]
        if not active_accounts:
            logger.error("Campaign %s: no active accounts", campaign_id)
            self._running[campaign_id] = False
            return {"error": "No active accounts available"}

        total_sent = 0
        total_failed = 0
        account_idx = 0
        iterations = 0

        while self._running.get(campaign_id):
            for group in groups:
                if not self._running.get(campaign_id):
                    break

                # Respect pause
                while self._paused.get(campaign_id):
                    await asyncio.sleep(1)
                    if not self._running.get(campaign_id):
                        break

                account = active_accounts[account_idx % len(active_accounts)]
                account_idx += 1

                for message in messages:
                    if not self._running.get(campaign_id):
                        break

                    try:
                        from app.services.telegram_service import TelegramService

                        svc = TelegramService(account)
                        await svc.send_message(group, message)
                        total_sent += 1
                        self._progress[campaign_id]["sent"] = total_sent
                        logger.debug(
                            "Campaign %s: sent to group %s via account %s",
                            campaign_id,
                            getattr(group, "group_id", group),
                            getattr(account, "phone", account),
                        )
                        if on_message_sent:
                            await on_message_sent(campaign_id, account, group, message)
                    except Exception as exc:
                        total_failed += 1
                        self._progress[campaign_id]["failed"] = total_failed
                        logger.warning(
                            "Campaign %s: failed sending to group %s: %s",
                            campaign_id,
                            getattr(group, "group_id", group),
                            exc,
                        )
                        if on_message_failed:
                            await on_message_failed(campaign_id, account, group, message, exc)

                    if on_progress:
                        await on_progress(campaign_id, self._progress[campaign_id])

                    # Anti-ban delay
                    delay = random.uniform(delay_min, delay_max)
                    await asyncio.sleep(delay)

            iterations += 1
            if not is_loop_infinite and iterations >= max(loop_count, 1):
                break

        self._running[campaign_id] = False
        result = {
            "campaign_id": campaign_id,
            "total_sent": total_sent,
            "total_failed": total_failed,
            "iterations": iterations,
            "completed_at": datetime.utcnow().isoformat(),
        }
        self._progress[campaign_id].update(result)
        logger.info("Campaign %s completed: %s", campaign_id, result)
        return result

    async def run_campaign_with_retry(
        self,
        campaign_id: int,
        queue_items: List[Any],
        max_retries: int = 3,
        on_progress: Optional[Callable] = None,
    ) -> Dict[str, Any]:
        """Process pre-built queue items with individual retry logic."""
        self._running[campaign_id] = True
        sent = 0
        failed = 0

        for item in queue_items:
            if not self._running.get(campaign_id):
                break

            while self._paused.get(campaign_id):
                await asyncio.sleep(1)

            for attempt in range(max_retries):
                try:
                    from app.services.telegram_service import TelegramService

                    svc = TelegramService(item.account)
                    await svc.send_message(item.group, item.message)
                    item.status = "sent"
                    item.processed_at = datetime.utcnow()
                    sent += 1
                    break
                except Exception as exc:
                    logger.warning(
                        "Campaign %s item %s attempt %s failed: %s",
                        campaign_id,
                        item.id,
                        attempt + 1,
                        exc,
                    )
                    item.retry_count = attempt + 1
                    item.error_message = str(exc)
                    if attempt == max_retries - 1:
                        item.status = "failed"
                        failed += 1
                    else:
                        await asyncio.sleep(2 ** attempt)

            if on_progress:
                await on_progress(campaign_id, {"sent": sent, "failed": failed})

        self._running[campaign_id] = False
        return {"sent": sent, "failed": failed}
