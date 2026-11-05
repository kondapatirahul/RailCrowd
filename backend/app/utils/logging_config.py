"""Structured application logging configuration."""

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from flask import Flask


def configure_logging(app: Flask) -> None:
    """Configure console and rotating-file logging for the application.

    Log files are stored under the Flask instance directory, which should not
    be committed to source control. The function avoids adding duplicate file
    handlers when multiple app instances are created during tests.
    """
    log_level_name = str(app.config.get("LOG_LEVEL", "INFO")).upper()
    log_level = getattr(logging, log_level_name, logging.INFO)

    log_directory = Path(app.instance_path) / "logs"
    log_directory.mkdir(parents=True, exist_ok=True)
    log_file = log_directory / "railcrowd.log"

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    )

    app.logger.setLevel(log_level)

    has_file_handler = any(
        isinstance(handler, RotatingFileHandler)
        and Path(handler.baseFilename) == log_file.resolve()
        for handler in app.logger.handlers
    )
    if not has_file_handler:
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=1_048_576,
            backupCount=5,
            encoding="utf-8",
        )
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
        app.logger.addHandler(file_handler)

    has_console_handler = any(
        getattr(handler, "_railcrowd_console_handler", False)
        for handler in app.logger.handlers
    )
    if not has_console_handler:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(log_level)
        console_handler.setFormatter(formatter)
        console_handler._railcrowd_console_handler = True
        app.logger.addHandler(console_handler)
