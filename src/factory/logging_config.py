"""Logging configuration for the pipeline.

Sets up structured JSON-line logging to both stderr and per-run log files.
"""
from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path


class JSONLineFormatter(logging.Formatter):
    """Formats log records as single-line JSON for machine parsing."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        if record.exc_info and record.exc_info[1]:
            log_entry["error"] = str(record.exc_info[1])
        return json.dumps(log_entry)


def setup_logging(
    level: str = "INFO",
    log_dir: str | Path = "logs",
    run_id: str | None = None,
) -> logging.Logger:
    """Configure logging for the pipeline.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR).
        log_dir: Directory for per-run log files.
        run_id: Optional run identifier for the log filename.

    Returns:
        The root logger.
    """
    root = logging.getLogger()
    root.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Clear existing handlers
    root.handlers.clear()

    # Stderr handler — human-readable
    stderr_handler = logging.StreamHandler(sys.stderr)
    stderr_handler.setFormatter(logging.Formatter(
        "%(asctime)s %(levelname)-8s %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    ))
    root.addHandler(stderr_handler)

    # File handler — JSON lines
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)

    if run_id is None:
        run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    file_handler = logging.FileHandler(log_path / f"run_{run_id}.json.log")
    file_handler.setFormatter(JSONLineFormatter())
    root.addHandler(file_handler)

    return root
