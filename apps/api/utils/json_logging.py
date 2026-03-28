import json
import logging
import os
import sys
import time
from typing import Any

# Service name for structured log identification (Task #98).
_SERVICE_NAME = os.getenv("SERVICE_NAME", "ai-real-estate-api")


class JsonFormatter(logging.Formatter):
    """Structured JSON log formatter with required fields (Task #98).

    Required fields: timestamp, level, service, message
    Optional fields (via extra): request_id, event, client_id, method, path,
                                  status, duration_ms
    """

    # Patterns that should never appear in log messages (sensitive data).
    _SENSITIVE_PATTERNS: tuple[str, ...] = (
        "password",
        "api_key",
        "secret",
        "token",
        "authorization",
        "cookie",
    )

    def format(self, record: logging.LogRecord) -> str:
        base: dict[str, Any] = {
            "ts": int(time.time() * 1000),
            "level": record.levelname,
            "service": _SERVICE_NAME,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for key in (
            "event",
            "request_id",
            "client_id",
            "method",
            "path",
            "status",
            "duration_ms",
        ):
            if hasattr(record, key):
                base[key] = getattr(record, key)

        # Include exception info if present
        if record.exc_info and record.exc_info[0] is not None:
            base["exception"] = self.formatException(record.exc_info)

        return json.dumps(base, ensure_ascii=False)

    @classmethod
    def check_sensitive_data(cls, message: str) -> list[str]:
        """Check if a log message contains sensitive data patterns.

        Returns list of matched pattern names (empty if clean).
        """
        lower = message.lower()
        return [p for p in cls._SENSITIVE_PATTERNS if p in lower]


def configure_json_logging(level: int = logging.INFO) -> None:
    """Configure root logger with structured JSON formatter."""
    logging.root.handlers.clear()
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    logging.root.addHandler(handler)
    logging.root.setLevel(level)
