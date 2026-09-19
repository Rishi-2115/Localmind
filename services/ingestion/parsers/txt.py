import logging

logger = logging.getLogger(__name__)

def parse_txt(file_path: str) -> str:
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        logger.error(f"Error parsing TXT {file_path}: {e}")
        return ""
