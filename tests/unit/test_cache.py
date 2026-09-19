import pytest
from unittest.mock import AsyncMock, patch
from ml.cache.semantic_cache import SemanticCache
import numpy as np

@pytest.mark.asyncio
async def test_semantic_cache_hit():
    cache = SemanticCache(threshold=0.9)
    cache._embed_query = AsyncMock(return_value=[1.0, 0.0])
    
    mock_redis = AsyncMock()
    mock_redis.keys.return_value = ["cache:t1:123"]
    mock_redis.get.return_value = '{"embedding": [1.0, 0.0], "response": "mock response"}'
    
    with patch("ml.cache.semantic_cache.redis_client", mock_redis):
        result = await cache.get_cached_response("t1", "test query")
        assert result == "mock response"

@pytest.mark.asyncio
async def test_semantic_cache_miss():
    cache = SemanticCache(threshold=0.9)
    cache._embed_query = AsyncMock(return_value=[1.0, 0.0])
    
    mock_redis = AsyncMock()
    mock_redis.keys.return_value = ["cache:t1:123"]
    # Orthogonal embedding should yield 0.0 similarity < 0.9 threshold
    mock_redis.get.return_value = '{"embedding": [0.0, 1.0], "response": "mock response"}'
    
    with patch("ml.cache.semantic_cache.redis_client", mock_redis):
        result = await cache.get_cached_response("t1", "test query")
        assert result is None
