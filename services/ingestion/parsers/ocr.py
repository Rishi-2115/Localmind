import logging
import io

logger = logging.getLogger(__name__)

try:
    import pytesseract
    from PIL import Image
    import fitz
except ImportError:
    pytesseract = None
    Image = None
    fitz = None


def ocr_pdf(file_path: str) -> str:
    if pytesseract is None or Image is None or fitz is None:
        logger.warning("pytesseract/Pillow/fitz not available for OCR fallback")
        return ""
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
