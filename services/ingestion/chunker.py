"""
Chunk text into fixed-size pieces with metadata preservation.

Chunks are roughly 512 words with 64-word overlap.
Metadata (page numbers, source doc) is preserved per chunk.
"""


def chunk_text(text: str, metadata: dict = None, chunk_size: int = 512, overlap: int = 64) -> list[dict]:
    """
    Split text into chunks while preserving metadata (e.g., page numbers).
    
    Args:
        text: Full text to chunk
        metadata: Optional dict with "page", "doc_id", etc. to carry through
        chunk_size: Number of words per chunk (roughly)
        overlap: Number of overlapping words between chunks
    
    Returns:
        [
            {
                "text": "chunk text",
                "chunk_idx": 0,
                "page": 1,  # if metadata provided
                "doc_id": "...",  # if metadata provided
            },
            ...
        ]
    """
    if metadata is None:
        metadata = {}
    
    words = text.split()
    chunks = []
    
    if not words:
        return chunks
    
    chunk_idx = 0
    start = 0
    while start < len(words):
        end = start + chunk_size
        chunk_text = " ".join(words[start:end])
        
        chunk = {
            "text": chunk_text,
            "chunk_idx": chunk_idx,
            "word_start": start,
            "word_end": end,
        }
        
        # Carry through metadata
        for key, value in metadata.items():
            chunk[key] = value
        
        chunks.append(chunk)
        chunk_idx += 1
        start += chunk_size - overlap
    
    return chunks
