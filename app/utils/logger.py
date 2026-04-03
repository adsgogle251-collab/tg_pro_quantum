import logging
import logging.config
import sys
from typing import Any, Dict


def get_log_config(debug: bool = False) -> Dict[str, Any]:
    level = "DEBUG" if debug else "INFO"
    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "detailed": {
                "format": (
                    "%(asctime)s | %(levelname)-8s | %(name)s:%(lineno)d | %(message)s"
                ),
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
            "simple": {
                "format": "%(levelname)s | %(name)s | %(message)s",
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "stream": "ext://sys.stdout",
                "formatter": "detailed",
                "level": level,
            },
        },
        "root": {
            "level": level,
            "handlers": ["console"],
        },
        "loggers": {
            "uvicorn": {"level": "INFO", "propagate": True},
            "uvicorn.error": {"level": "INFO", "propagate": True},
            "uvicorn.access": {"level": "WARNING", "propagate": True},
            "sqlalchemy.engine": {
                "level": "DEBUG" if debug else "WARNING",
                "propagate": True,
            },
            "telethon": {"level": "WARNING", "propagate": True},
        },
    }


def setup_logging(debug: bool = False) -> None:
    logging.config.dictConfig(get_log_config(debug))


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
