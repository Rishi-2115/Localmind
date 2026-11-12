import logging

logger = logging.getLogger(__name__)

try:
    import docx
except ImportError:
    docx = None


def parse_docx(file_path: str) -> str:
    if docx is None:
        logger.error("python-docx is not installed in the current environment")
        return ""
    try:
        doc = docx.Document(file_path)
        text = "\n".join([paragraph.text for paragraph in doc.paragraphs])
        return text
    except Exception as e:
        logger.error(f"Error parsing DOCX {file_path}: {e}")
        return ""
