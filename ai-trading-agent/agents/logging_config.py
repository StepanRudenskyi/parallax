import json
import logging
import sys
import time


class JsonFormatter(logging.Formatter):
    """
    Minimal JSON line formatter -- no external dependency (e.g. python-json-logger)
    needed for something this small. Each log line is one JSON object, which
    makes it trivial to grep/parse later or feed into a log aggregator if this
    project ever gets deployed somewhere that has one.
    """

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        # Extra structured fields passed via logger.info(..., extra={...})
        for key, value in record.__dict__.items():
            if key in ("ticker", "duration_ms", "verdict", "confidence", "agent", "status"):
                payload[key] = value
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload)


def configure_logging(level: int = logging.INFO) -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())

    root = logging.getLogger()
    root.setLevel(level)
    root.handlers = [handler]

    # Quiet down noisy third-party libraries at INFO level.
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)


class Timer:
    """Small context manager to measure and log node duration consistently."""

    def __init__(self, logger: logging.Logger, label: str, **extra):
        self.logger = logger
        self.label = label
        self.extra = extra
        self.start = None

    def __enter__(self):
        self.start = time.perf_counter()
        self.logger.info(f"{self.label} started", extra=self.extra)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        duration_ms = round((time.perf_counter() - self.start) * 1000, 1)
        if exc_type is None:
            self.logger.info(
                f"{self.label} completed",
                extra={**self.extra, "duration_ms": duration_ms, "status": "ok"},
            )
        else:
            self.logger.error(
                f"{self.label} failed: {exc_val}",
                extra={**self.extra, "duration_ms": duration_ms, "status": "error"},
            )
        return False  # do not swallow exceptions