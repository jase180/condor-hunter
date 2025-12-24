"""Logging configuration for Iron Condor Screener.

Provides structured logging with configurable levels and outputs.
"""

import logging
import sys
from typing import Optional
from pathlib import Path


def setup_logging(
    log_level: str = "INFO",
    log_file: Optional[str] = None,
    log_format: Optional[str] = None,
) -> logging.Logger:
    """Configure structured logging for the application.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional path to log file. If None, logs only to console.
        log_format: Optional custom log format string

    Returns:
        Configured logger instance

    Example:
        >>> logger = setup_logging(log_level="DEBUG", log_file="screener.log")
        >>> logger.info("Starting screening workflow")
        >>> logger.warning("IV rank %s below minimum %s", 35.0, 40.0)
    """
    logger = logging.getLogger("condor_screener")
    logger.setLevel(getattr(logging, log_level.upper()))

    # Clear any existing handlers to avoid duplicates
    logger.handlers.clear()

    # Default format with timestamp, level, module, and message
    if log_format is None:
        log_format = '%(asctime)s - %(name)s - %(levelname)s - %(module)s:%(lineno)d - %(message)s'

    formatter = logging.Formatter(log_format, datefmt='%Y-%m-%d %H:%M:%S')

    # Console handler (stdout)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File handler if specified
    if log_file:
        # Create directory if it doesn't exist
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(log_file, mode='a')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    # Prevent propagation to root logger
    logger.propagate = False

    return logger


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """Get a logger instance.

    Args:
        name: Optional logger name. If None, returns the root screener logger.

    Returns:
        Logger instance

    Example:
        >>> logger = get_logger(__name__)
        >>> logger.debug("Processing option with strike %s", 550.0)
    """
    if name:
        return logging.getLogger(f"condor_screener.{name}")
    return logging.getLogger("condor_screener")


# Create default logger instance
logger = setup_logging()
