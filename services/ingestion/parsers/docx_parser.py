import docx
import logging

logger = logging.getLogger(__name__)

def parse_docx(file_path: str) -> str:
    try:
        doc = docx.Document(file_path)
        text = "\n".join([paragraph.text for paragraph in doc.paragraphs])
        return text
    except Exception as e:
        logger.error(f"Error parsing DOCX {file_path}: {e}")
        return ""
