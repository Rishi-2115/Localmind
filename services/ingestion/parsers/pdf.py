"""
PDF parser with page number tracking for citations.

Returns:
{
    "text": "...",
    "chunks": [
        {"text": "chunk text", "page": 1, "start_char": 0, "end_char": 500},
        ...
    ]
}
"""
import fitz  # PyMuPDF
import logging

logger = logging.getLogger(__name__)


def parse_pdf(file_path: str) -> dict:
    """
    Parse PDF with page-level metadata for citations.
    
    Args:
        file_path: Path to PDF file (local or MinIO path after download)
    
    Returns:
        {
            "text": full text concatenated,
            "chunks_with_metadata": [
                {"text": str, "page": int, "start_char": int, "end_char": int}
            ]
        }
    """
    try:
        doc = fitz.open(file_path)
        full_text = ""
        chunks_with_metadata = []
        
        for page_num, page in enumerate(doc, start=1):
            page_text = page.get_text()
            start_char = len(full_text)
            full_text += page_text
            end_char = len(full_text)
            
            # Store metadata for this page's text
            if page_text.strip():
                chunks_with_metadata.append({
                    "text": page_text,
                    "page": page_num,
                    "start_char": start_char,
                    "end_char": end_char,
                })
        
        logger.info(f"Parsed PDF {file_path}: {len(chunks_with_metadata)} pages")
        return {
            "text": full_text,
            "chunks_with_metadata": chunks_with_metadata,
            "total_pages": len(doc),
        }
    except Exception as e:
        logger.error(f"Error parsing PDF {file_path}: {e}")
        return {
            "text": "",
            "chunks_with_metadata": [],
            "total_pages": 0,
            "error": str(e),
        }
