import pytesseract
from PIL import Image
import fitz
import io
import logging

logger = logging.getLogger(__name__)

def ocr_pdf(file_path: str) -> str:
    try:
        doc = fitz.open(file_path)
        text = ""
        for page in doc:
            pix = page.get_pixmap()
            img = Image.open(io.BytesIO(pix.tobytes("png")))
            text += pytesseract.image_to_string(img) + "\n"
        return text
    except Exception as e:
        logger.error(f"Error performing OCR on PDF {file_path}: {e}")
        return ""
