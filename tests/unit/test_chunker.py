import pytest
from services.ingestion.chunker import chunk_text

def test_chunk_text_basic():
    # Generate 1000 words
    words = [f"word{i}" for i in range(1000)]
    text = " ".join(words)

    chunk_size = 512
    overlap = 64
    chunks = chunk_text(text, metadata={"doc_id": "test_doc", "page": 3}, chunk_size=chunk_size, overlap=overlap)

    # Step size is chunk_size - overlap = 512 - 64 = 448 words per step
    # 1000 words:
    # chunk 0: 0 to 512
    # chunk 1: 448 to 960
    # chunk 2: 896 to 1000
    # Total = 3 chunks
    assert len(chunks) == 3

    for chunk in chunks:
        chunk_word_count = len(chunk["text"].split())
        assert chunk_word_count <= chunk_size
        assert chunk["doc_id"] == "test_doc"
        assert chunk["page"] == 3

def test_chunk_text_empty():
    chunks = chunk_text("", metadata={"doc_id": "empty"})
    assert chunks == []

def test_chunk_text_smaller_than_chunk_size():
    text = "This is a brief legal clause that is well under 512 words."
    chunks = chunk_text(text, metadata={"page": 1})
    assert len(chunks) == 1
    assert chunks[0]["text"] == text
    assert chunks[0]["chunk_idx"] == 0
    assert chunks[0]["page"] == 1
