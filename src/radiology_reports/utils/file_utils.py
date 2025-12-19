# src/radiology_reports/utils/file_utils.py

import os
from datetime import datetime, timedelta
import logging
from pydantic_settings import BaseSettings, SettingsConfigDict

class AppConfig(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', env_ignore_empty=True, extra='ignore')

    report_retention_days: int = 30

# In cleanup_old_files
config = AppConfig()
retention_days = config.report_retention_days

logger = logging.getLogger(__name__)

def cleanup_old_files(output_root: str, retention_days: int = 30):
    """
    Deletes PDF files in the output directory older than the specified retention days.
    
    :param output_root: Path to the output directory.
    :param retention_days: Number of days to retain files (default: 30).
    """
    today = datetime.now()
    cutoff = today - timedelta(days=retention_days)
    
    if not os.path.exists(output_root):
        logger.warning(f"Output directory does not exist: {output_root}")
        return

    deleted_count = 0
    for filename in os.listdir(output_root):
        if filename.endswith(".pdf"):
            file_path = os.path.join(output_root, filename)
            file_mtime = datetime.fromtimestamp(os.path.getmtime(file_path))
            if file_mtime < cutoff:
                try:
                    os.remove(file_path)
                    logger.info(f"Deleted old file: {file_path}")
                    deleted_count += 1
                except Exception as e:
                    logger.error(f"Error deleting {file_path}: {e}")

    logger.info(f"Cleanup complete: {deleted_count} files deleted from {output_root}.")