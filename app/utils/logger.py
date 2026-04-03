"""
TG PRO QUANTUM - Structured logging utility
"""
import logging
import sys
from app.config import settings

LOG_LEVEL = logging.DEBUG if settings.DEBUG else logging.INFO

logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)],
)


def get_logger(name: str) -> logging.Logger:
    """Return a named logger."""
    return logging.getLogger(name)


logger = get_logger("tg_quantum")
