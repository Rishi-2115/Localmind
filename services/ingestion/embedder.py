"""
Embed text chunks using Ollama's nomic-embed-text model.

Validates embedding dimensions on startup.
"""
import httpx
import os
import logging
import asyncio

logger = logging.getLogger(__name__)

OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://ollama:11434")
EMBEDDING_MODEL = "nomic-embed-text"
EXPECTED_EMBEDDING_DIM = 768


async def validate_embedding_model():
    """
    On startup, verify that Ollama's embedding model outputs the expected dimension.
    This prevents silent FAISS corruption if the model changes or is swapped.
    """
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{OLLAMA_BASE_URL}/api/embed",
                json={"model": EMBEDDING_MODEL, "input": "test"},
            )
            response.raise_for_status()
            embedding = response.json()["embeddings"][0]
            actual_dim = len(embedding)
            
            if actual_dim != EXPECTED_EMBEDDING_DIM:
                raise RuntimeError(
                    f"Embedding dimension mismatch! Expected {EXPECTED_EMBEDDING_DIM}, "
                    f"got {actual_dim}. Model change detected or wrong model deployed."
                )
            logger.info(f"✓ Embedding model validated: {EMBEDDING_MODEL} ({actual_dim}D)")
    except Exception as e:
        logger.error(f"✗ Embedding model validation failed: {e}")
        raise


def embed_texts(texts: list[str]) -> list[list[float]]:
    """
    Embed a list of text chunks using Ollama.
    
    Args:
        texts: List of text strings to embed
    
    Returns:
        List of embedding vectors (each 768-dimensional)
    """
    embeddings = []
    with httpx.Client(timeout=30.0) as client:
        for i, text in enumerate(texts):
            try:
                response = client.post(
                    f"{OLLAMA_BASE_URL}/api/embed",
                    json={"model": EMBEDDING_MODEL, "input": text}
                )
                response.raise_for_status()
                embedding = response.json()["embeddings"][0]
                
                # Validate dimension
                if len(embedding) != EXPECTED_EMBEDDING_DIM:
                    raise ValueError(
                        f"Unexpected embedding dimension {len(embedding)}, expected {EXPECTED_EMBEDDING_DIM}"
                    )
                
                embeddings.append(embedding)
                logger.debug(f"Embedded chunk {i+1}/{len(texts)}")
            except Exception as e:
                logger.error(f"Error embedding text chunk {i}: {e}")
                # Return zero vector as fallback (will be penalized in FAISS retrieval)
                embeddings.append([0.0] * EXPECTED_EMBEDDING_DIM)
    
    logger.info(f"Embedded {len(embeddings)} chunks")
    return embeddings
