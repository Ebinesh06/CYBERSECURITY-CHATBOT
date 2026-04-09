"""
logger.py — Structured logging for production.

In development: human-friendly coloured output.
In production: newline-delimited JSON for log aggregators (Datadog, CloudWatch).
"""

import logging
import sys
import json
from datetime import datetime, timezone


class JSONFormatter(logging.Formatter):
    """Emit each log record as a single-line JSON object."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload)


def get_logger(name: str = "cybersec_chatbot") -> logging.Logger:
    """Return a configured logger (cached by name)."""
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger  # already configured — avoid duplicate handlers

    logger.setLevel(logging.DEBUG)
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.DEBUG)

    # Use JSON in production, plain text otherwise
    import os
    if os.getenv("APP_ENV", "development") == "production":
        handler.setFormatter(JSONFormatter())
    else:
        handler.setFormatter(
            logging.Formatter(
                fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
                datefmt="%H:%M:%S",
            )
        )

    logger.addHandler(handler)
    logger.propagate = False
    return logger
