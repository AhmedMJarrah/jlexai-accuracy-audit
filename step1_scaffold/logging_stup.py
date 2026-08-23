"""
Structured logging: every log line is a JSON object written to
logs/pipe.log (parseable later — e.g. to audit who ran what, when),
plus a human-readable stream to the console.
"""
import json
import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
            "level": record.levelname,
            "logger": record.name,
            "module": record.module,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def setup_logging(log_dir: Path, log_level: str = "INFO") -> None:
    root = logging.getLogger()
    root.setLevel(log_level.upper())

    # avoid duplicate handlers if setup_logging() gets called twice
    if root.handlers:
        return

    file_handler = RotatingFileHandler(
        log_dir / "pipe.log", maxBytes=5_000_000, backupCount=5, encoding="utf-8"
    )
    file_handler.setFormatter(JsonFormatter())
    root.addHandler(file_handler)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(
        logging.Formatter("%(asctime)s | %(levelname)-8s | %(name)s | %(message)s")
    )
    root.addHandler(console_handler)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)