import json
import logging
import os
from redis.asyncio import Redis
import numpy as np
import httpx

logger = logging.getLogger(__name__)

REDIS_URL = os.environ.get("REDIS_URL", "redis://redis:6379/0")
OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://ollama:11434")
EMBEDDING_MODEL = os.environ.get("EMBEDDING_MODEL", "nomic-embed-text")

redis_client = Redis.from_url(REDIS_URL, decode_responses=True)

class SemanticCache:
    def __init__(self, threshold=0.92, ttl=3600):
        self.threshold = threshold
        self.ttl = ttl

    async def _embed_query(self, query: str) -> list[float]:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{OLLAMA_BASE_URL}/api/embeddings",
                json={"model": EMBEDDING_MODEL, "prompt": query}
            )
            response.raise_for_status()
            return response.json()["embedding"]

    async def get_cached_response(self, tenant_id: str, query: str):
        try:
            query_emb = await self._embed_query(query)
            query_vec = np.array(query_emb)
            norm_q = np.linalg.norm(query_vec)
            if norm_q > 0:
                query_vec = query_vec / norm_q

            cache_keys = await redis_client.keys(f"cache:{tenant_id}:*")
            best_match = None
            best_score = -1

            for key in cache_keys:
                cached_data = await redis_client.get(key)
                if cached_data:
                    data = json.loads(cached_data)
                    cached_emb = np.array(data["embedding"])
                    
                    score = np.dot(query_vec, cached_emb)
                    if score > self.threshold and score > best_score:
                        best_score = score
                        best_match = data["response"]
            
            if best_match:
                logger.info(f"Semantic cache hit for tenant {tenant_id}. Score: {best_score}")
                return best_match
            return None
        except Exception as e:
            logger.error(f"Error checking semantic cache: {e}")
            return None

    async def set_cache(self, tenant_id: str, query: str, response: str):
        try:
            query_emb = await self._embed_query(query)
            query_vec = np.array(query_emb)
            norm_q = np.linalg.norm(query_vec)
            if norm_q > 0:
                query_vec = query_vec / norm_q

            data = {
                "query": query,
                "embedding": query_vec.tolist(),
                "response": response
            }
            key_hash = hash(query)
            key = f"cache:{tenant_id}:{key_hash}"
            await redis_client.setex(key, self.ttl, json.dumps(data))
        except Exception as e:
            logger.error(f"Error setting semantic cache: {e}")

semantic_cache = SemanticCache()
