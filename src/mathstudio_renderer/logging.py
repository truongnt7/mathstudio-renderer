"""Structured JSON logging for the renderer."""

from __future__ import annotations

import logging
import sys
from typing import Any

import orjson


class JsonFormatter(logging.Formatter):
    """Emit log records as newline-delimited JSON."""

    def format(self, record: logging.LogRecord) -> str:
        data: dict[str, Any] = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            data["exception"] = self.formatException(record.exc_info)
        # Merge any extra fields attached to the record
        for key, val in record.__dict__.items():
            if key not in {
                "name",
                "msg",
                "args",
                "levelname",
                "levelno",
                "pathname",
                "filename",
                "module",
                "exc_info",
                "exc_text",
                "stack_info",
                "lineno",
                "funcName",
                "created",
                "msecs",
                "relativeCreated",
                "thread",
                "threadName",
                "processName",
                "process",
                "message",
                "taskName",
            }:
                data[key] = val
        return orjson.dumps(data).decode()


class TextFormatter(logging.Formatter):
    """Human-readable formatter for development."""

    _FMT = "%(asctime)s %(levelname)-8s %(name)s — %(message)s"
    _DATEFMT = "%H:%M:%S"

    def __init__(self) -> None:
        super().__init__(fmt=self._FMT, datefmt=self._DATEFMT)


def configure_logging(level: str = "INFO", fmt: str = "json") -> None:
    """Install the root handler.  Call once at startup."""
    root = logging.getLogger()
    root.setLevel(getattr(logging, level.upper(), logging.INFO))

    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(JsonFormatter() if fmt == "json" else TextFormatter())

    root.handlers.clear()
    root.addHandler(handler)

    # Silence noisy third-party loggers
    for noisy in ("PIL", "fontTools", "manim", "urllib3"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
