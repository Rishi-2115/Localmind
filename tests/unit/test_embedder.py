import pytest
from unittest.mock import patch, MagicMock
from services.ingestion.embedder import validate_embedding_model, embed_texts, EXPECTED_EMBEDDING_DIM

@pytest.mark.asyncio
async def test_validate_embedding_model_success():
    mock_response = MagicMock()
    mock_response.json.return_value = {"embedding": [0.1] * EXPECTED_EMBEDDING_DIM}
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient.post", return_value=mock_response):
        # Should complete without error
        await validate_embedding_model()

@pytest.mark.asyncio
async def test_validate_embedding_model_dimension_mismatch():
    mock_response = MagicMock()
    # Return 384 dimensions instead of 768
    mock_response.json.return_value = {"embedding": [0.1] * 384}
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient.post", return_value=mock_response):
        with pytest.raises(RuntimeError) as exc_info:
            await validate_embedding_model()
        assert "Embedding dimension mismatch" in str(exc_info.value)
        assert f"Expected {EXPECTED_EMBEDDING_DIM}" in str(exc_info.value)

def test_embed_texts_dimension_mismatch():
    mock_response = MagicMock()
    mock_response.json.return_value = {"embedding": [0.1] * 512}  # Mismatched dim
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.Client.post", return_value=mock_response):
        # When dimension is mismatched, embed_texts logs error and returns fallback zero vector of expected dim
        embeddings = embed_texts(["clause text"])
        assert len(embeddings) == 1
        assert len(embeddings[0]) == EXPECTED_EMBEDDING_DIM
        # fallback is zeros
        assert all(v == 0.0 for v in embeddings[0])
