# logs/logger.py
import logging
import os
from logging.handlers import TimedRotatingFileHandler

# Ensure logs directory exists
LOG_DIR = os.path.dirname(os.path.abspath(__file__))
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)


def get_logger(name: str, log_file: str, level=logging.INFO) -> logging.Logger:
    """
    Create a logger with TimedRotatingFileHandler (rotates daily).

    Args:
        name (str): Logger name.
        log_file (str): File name for logs.
        level (int): Logging level.

    Returns:
        logging.Logger: Configured logger.
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Avoid duplicate handlers if logger already exists
    if not logger.handlers:
        file_path = os.path.join(LOG_DIR, log_file)
        handler = TimedRotatingFileHandler(file_path, when="midnight", backupCount=7, encoding="utf-8")
        handler.setLevel(level)

        formatter = logging.Formatter(
            "%(asctime)s - [%(levelname)s] - %(name)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        handler.setFormatter(formatter)

        logger.addHandler(handler)

    return logger


# --- Define specific loggers ---
req_logger = get_logger("requests", "requests.log", logging.INFO)
err_logger = get_logger("errors", "errors.log", logging.ERROR)
fetch_logger = get_logger("fetcher", "fetcher.log", logging.INFO)
