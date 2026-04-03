"""
TG PRO QUANTUM - Shared Celery async helper
"""
import asyncio


def run_async(coro):
    """Run an async coroutine inside a Celery (sync) worker."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()
