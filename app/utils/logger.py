from __future__ import annotations

import logging
from logging import Logger
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional

from config.settings import get_settings

_logging_configured: bool = False


class _ColorFormatter(logging.Formatter):
    """Formatter that adds ANSI color codes based on log level.

    This formatter is used for console output only and leaves file logging
    uncolored for easier parsing and archival.
    """

    _COLORS = {
        "DEBUG": "\033[36m",  # Cyan
        "INFO": "\033[32m",  # Green
        "WARNING": "\033[33m",  # Yellow
        "ERROR": "\033[31m",  # Red
        "CRITICAL": "\033[41m",  # Red background
    }
    _RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        """Return the formatted log record with color codes applied.

        Args:
            record: The log record to format.

        Returns:
            str: The formatted log message with ANSI color codes applied.
        """

        base_message = super().format(record)
        color = self._COLORS.get(record.levelname, "")
        if not color:
            return base_message
        return f"{color}{base_message}{self._RESET}"


def _configure_logging() -> None:
    """Configure the root logger based on application settings.

    This function is idempotent and safe to call multiple times. It reads
    logging configuration values (log level and log file path) from the
    application `Settings` object and applies them to the root logger.

    Configuration includes:
    * A rotating file handler (10MB max, 3 backups) using ``LOG_FILE``.
    * A console handler with colored output using ``LOG_LEVEL``.
    """

    global _logging_configured
    if _logging_configured:
        return

    settings = get_settings()

    log_level: int = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    log_file: Optional[Path] = settings.LOG_FILE

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Clear existing handlers to avoid duplicates in interactive environments.
    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)

    # Console handler with colored output.
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(
        _ColorFormatter(
            fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )
    root_logger.addHandler(console_handler)

    # Rotating file handler (if configured).
    if log_file:
        log_file_path = Path(log_file)
        log_file_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = RotatingFileHandler(
            log_file_path,
            maxBytes=10 * 1024 * 1024,  # 10 MB
            backupCount=3,
            encoding="utf-8",
        )
        file_handler.setLevel(log_level)
        file_handler.setFormatter(
            logging.Formatter(
                fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )
        root_logger.addHandler(file_handler)

    _logging_configured = True


def get_logger(name: str) -> Logger:
    """Return a configured logger instance for the given name.

    The first time this function is called, it configures global logging based
    on application settings (via :func:`_configure_logging`). Configuration
    includes a rotating file handler (10MB max, 3 backups) and a colored
    console handler.

    Args:
        name: The logger name, typically ``__name__`` of the calling module.

    Returns:
        Logger: A standard library :class:`logging.Logger` instance configured
        with the application's logging settings.
    """

    _configure_logging()
    return logging.getLogger(name)

