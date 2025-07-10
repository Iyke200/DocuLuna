import logging
import os
from datetime import datetime, timedelta
import glob

logger = logging.getLogger(__name__)

def cleanup_old_files(directory: str, days: int = 7):
    threshold = datetime.now() - timedelta(days=days)
    for file_path in glob.glob(f"{directory}/*"):
        if os.path.isfile(file_path):
            file_mtime = datetime.fromtimestamp(os.path.getmtime(file_path))
            if file_mtime < threshold:
                try:
                    os.remove(file_path)
                    logger.info("Deleted old file: %s", file_path)
                except Exception as e:
                    logger.error("Failed to delete %s: %s", file_path, e)