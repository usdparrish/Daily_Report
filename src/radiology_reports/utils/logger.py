# utils/logger.py
import logging
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Ensure logs directory exists
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

# Get config from .env (with safe defaults)
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
LOG_FILE = os.getenv("LOG_FILE", LOG_DIR / "daily_report.log")

# Create formatter
formatter = logging.Formatter(
    fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(filename)s:%(lineno)d | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

# File handler
file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
file_handler.setLevel(LOG_LEVEL)
file_handler.setFormatter(formatter)

# Console handler (for local runs)
console_handler = logging.StreamHandler()
console_handler.setLevel("INFO")  # Always show INFO+ in console
console_handler.setFormatter(formatter)

def get_logger(name: str = "radiology_reports") -> logging.Logger:
    """Return a configured logger instance."""
    logger = logging.getLogger(name)
    logger.setLevel(LOG_LEVEL)
    
    # Avoid duplicate handlers if called multiple times
    if not logger.handlers:
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
    
    return logger