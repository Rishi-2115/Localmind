import os
import faiss
import numpy as np
import boto3
import json
import logging
from collections import OrderedDict

# Avoid AWS IMDS hang on non-EC2/Windows environments
os.environ.setdefault("AWS_EC2_METADATA_DISABLED", "true")

logger = logging.getLogger(__name__)

MINIO_ENDPOINT = os.environ.get("MINIO_ENDPOINT", "minio:9000")
MINIO_ACCESS_KEY = os.environ.get("MINIO_ACCESS_KEY", "minioadmin")
MINIO_SECRET_KEY = os.environ.get("MINIO_SECRET_KEY", "minioadmin")
REDIS_URL = os.environ.get("REDIS_URL", "redis://redis:6379/0")

_s3_client = None


def get_s3_client():
    global _s3_client
    if _s3_client is None:
        _s3_client = boto3.client(
            's3',
            endpoint_url=f"http://{MINIO_ENDPOINT}",
            aws_access_key_id=MINIO_ACCESS_KEY,
            aws_secret_access_key=MINIO_SECRET_KEY,
            region_name=os.environ.get("AWS_DEFAULT_REGION", "us-east-1"),
        )
    return _s3_client


class IndexLRUCache:
    """
    In-process LRU cache for loaded FAISS indexes and metadata.
    Keyed by (tenant_id, index_version).
    Thread-safe and async-compatible.
    """
    def __init__(self, maxsize: int = 32):
        self.maxsize = maxsize
        self._cache = OrderedDict()  # (tenant_id, version) -> (index, metadata)

    def get(self, tenant_id: str, version: str):
        key = (tenant_id, str(version))
        if key in self._cache:
            self._cache.move_to_end(key)
            logger.debug(f"[LRU Cache HIT] tenant={tenant_id} version={version}")
            return self._cache[key]
        logger.debug(f"[LRU Cache MISS] tenant={tenant_id} version={version}")
        return None

    def put(self, tenant_id: str, version: str, index, metadata: dict):
        key = (tenant_id, str(version))
        if key in self._cache:
            self._cache.move_to_end(key)
        self._cache[key] = (index, metadata)
        if len(self._cache) > self.maxsize:
            evicted_key, _ = self._cache.popitem(last=False)
            logger.debug(f"[LRU Cache EVICT] {evicted_key}")

    def invalidate(self, tenant_id: str = None):
        """Invalidate entries for a specific tenant or all entries."""
        if tenant_id is None:
            self._cache.clear()
            logger.info("[LRU Cache] Cleared all indexes")
        else:
            keys_to_remove = [k for k in self._cache.keys() if k[0] == tenant_id]
            for k in keys_to_remove:
                del self._cache[k]
            logger.info(f"[LRU Cache] Invalidated entries for tenant={tenant_id}")


class Retriever:
    def __init__(self, cache_maxsize: int = 32):
        self.local_index_path = "/tmp/faiss_indexes"
        os.makedirs(self.local_index_path, exist_ok=True)
        self.cache = IndexLRUCache(maxsize=cache_maxsize)
        self._redis_client = None

    def _get_redis(self):
        if self._redis_client is None:
            try:
                import socket
                from urllib.parse import urlparse
                import redis.asyncio as aioredis

                parsed = urlparse(REDIS_URL)
                host = parsed.hostname or "localhost"
                port = parsed.port or 6379

                # Quick probe to avoid 30s asyncio DNS retry loops if Redis is unreachable
                probe = socket.create_connection((host, port), timeout=0.3)
                probe.close()

                self._redis_client = aioredis.from_url(
                    REDIS_URL,
                    decode_responses=True,
                    socket_timeout=1.0,
                    socket_connect_timeout=1.0,
                    retry_on_timeout=False,
                )
            except Exception as e:
                logger.debug(f"Redis unavailable for index versioning ({e})")
                self._redis_client = False
        return self._redis_client if self._redis_client is not False else None

    def _get_tenant_index_path(self, tenant_id: str):
        return os.path.join(self.local_index_path, f"{tenant_id}.index")

    def _get_tenant_metadata_path(self, tenant_id: str):
        return os.path.join(self.local_index_path, f"{tenant_id}_meta.json")

    async def get_index_version(self, tenant_id: str) -> str:
        """
        Fetch current index version from Redis or fallback to local file mtime.
        """
        if os.environ.get("LOCALMIND_TESTING"):
            index_file = self._get_tenant_index_path(tenant_id)
            if os.path.exists(index_file):
                return str(int(os.path.getmtime(index_file)))
            return "0"

        try:
            r = self._get_redis()
            if r:
                ver = await r.get(f"index:version:{tenant_id}")
                if ver is not None:
                    return str(ver)
        except Exception as e:
            logger.debug(f"Redis version lookup failed: {e}")

        # Fallback to file mtime if available
        index_file = self._get_tenant_index_path(tenant_id)
        if os.path.exists(index_file):
            return str(int(os.path.getmtime(index_file)))
        return "0"

    async def _download_index(self, tenant_id: str):
        bucket_name = f"tenant-{tenant_id}"
        index_file = self._get_tenant_index_path(tenant_id)
        meta_file = self._get_tenant_metadata_path(tenant_id)
        
        try:
            client = get_s3_client()
            client.download_file(bucket_name, "faiss.index", index_file)
            client.download_file(bucket_name, "metadata.json", meta_file)
            return True
        except Exception as e:
            logger.error(f"Could not download index for tenant {tenant_id}: {e}")
            return False

    async def _load_index_and_metadata(self, tenant_id: str, version: str):
        """
        Load index and metadata from cache or disk, downloading from MinIO if missing.
        """
        # 1. Check in-process LRU cache
        cached = self.cache.get(tenant_id, version)
        if cached is not None:
            return cached

        # 2. Check disk / download from MinIO
        index_file = self._get_tenant_index_path(tenant_id)
        meta_file = self._get_tenant_metadata_path(tenant_id)
        
        if not os.path.exists(index_file) or not os.path.exists(meta_file):
            if os.environ.get("LOCALMIND_TESTING"):
                return None, None
            success = await self._download_index(tenant_id)
            if not success:
                return None, None

        try:
            index = faiss.read_index(index_file)
            with open(meta_file, 'r', encoding='utf-8') as f:
                metadata = json.load(f)

            # Store in in-process LRU cache
            self.cache.put(tenant_id, version, index, metadata)
            return index, metadata
        except Exception as e:
            logger.error(f"Error loading index for tenant {tenant_id}: {e}")
            return None, None

    async def retrieve(self, tenant_id: str, query_embedding: list[float], top_k: int = 5):
        version = await self.get_index_version(tenant_id)
        index, metadata = await self._load_index_and_metadata(tenant_id, version)
        if index is None or metadata is None:
            return []

        try:
            query_vec = np.array([query_embedding], dtype=np.float32)
            faiss.normalize_L2(query_vec)
            
            distances, indices = index.search(query_vec, top_k)
            
            results = []
            for idx in indices[0]:
                if idx != -1 and str(idx) in metadata:
                    results.append(metadata[str(idx)])
            
            return results
        except Exception as e:
            logger.error(f"Error during retrieval for tenant {tenant_id}: {e}")
            return []


retriever = Retriever()
