"""
FAISS indexing with metadata preservation for page-level citations.

Stores chunks with their page numbers, document IDs, and text snippets
for later retrieval and citation generation.

Includes:
- Per-tenant distributed Redis locking for concurrency safety
- Auto-switching to HNSW or IVF-PQ index above configurable vector count
- Index version incrementing for retriever LRU cache invalidation
"""
import faiss
import numpy as np
import os
import json
import boto3
import logging
import threading
from contextlib import contextmanager

# Avoid AWS IMDS hang on non-EC2/Windows environments
os.environ.setdefault("AWS_EC2_METADATA_DISABLED", "true")

logger = logging.getLogger(__name__)

MINIO_ENDPOINT = os.environ.get("MINIO_ENDPOINT", "minio:9000")
MINIO_ACCESS_KEY = os.environ.get("MINIO_ACCESS_KEY", "minioadmin")
MINIO_SECRET_KEY = os.environ.get("MINIO_SECRET_KEY", "minioadmin")
REDIS_URL = os.environ.get("REDIS_URL", os.environ.get("CELERY_BROKER_URL", "redis://redis:6379/0"))

# Threshold for auto-switching from Flat to HNSW/IVF-PQ (Default 10,000 vectors)
FAISS_SWITCH_THRESHOLD = int(os.environ.get("FAISS_SWITCH_THRESHOLD", "10000"))
FAISS_LARGE_INDEX_TYPE = os.environ.get("FAISS_LARGE_INDEX_TYPE", "HNSW")  # HNSW or IVF-PQ

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

EXPECTED_EMBEDDING_DIM = 768

# Local in-process fallback locks when Redis is unreachable
_local_locks = {}
_local_locks_mutex = threading.Lock()


def _get_local_lock(tenant_id: str):
    with _local_locks_mutex:
        if tenant_id not in _local_locks:
            _local_locks[tenant_id] = threading.Lock()
        return _local_locks[tenant_id]


@contextmanager
def tenant_index_lock(tenant_id: str, timeout: int = 120):
    """
    Acquire a per-tenant lock using Redis distributed lock.
    Falls back to in-process threading lock if Redis is unavailable.
    """
    lock_key = f"lock:index:{tenant_id}"
    redis_client = None
    redis_lock = None
    try:
        import redis
        redis_client = redis.Redis.from_url(REDIS_URL, socket_timeout=2.0)
        # Test connection quickly
        redis_client.ping()
        redis_lock = redis_client.lock(lock_key, timeout=timeout, blocking_timeout=60)
    except Exception as e:
        logger.debug(f"Redis distributed lock unavailable ({e}), using in-process lock")
        redis_lock = None

    if redis_lock is not None:
        acquired = redis_lock.acquire()
        if not acquired:
            raise TimeoutError(f"Could not acquire distributed lock for tenant {tenant_id}")
        try:
            yield
        finally:
            try:
                redis_lock.release()
            except Exception:
                pass
    else:
        # Fallback to local threading lock
        local_lock = _get_local_lock(tenant_id)
        with local_lock:
            yield


def _get_local_paths(tenant_id: str):
    """Get local paths for FAISS index and metadata."""
    base = "/tmp/faiss_indexes"
    os.makedirs(base, exist_ok=True)
    return os.path.join(base, f"{tenant_id}.index"), os.path.join(base, f"{tenant_id}_meta.json")


def _download_index(tenant_id: str, index_file: str, meta_file: str):
    """Download existing FAISS index and metadata from MinIO."""
    bucket_name = f"tenant-{tenant_id}"
    s3 = get_s3_client()
    try:
        s3.head_bucket(Bucket=bucket_name)
    except Exception:
        logger.info(f"Creating MinIO bucket {bucket_name}")
        try:
            s3.create_bucket(Bucket=bucket_name)
        except Exception:
            pass

    try:
        s3.download_file(bucket_name, "faiss.index", index_file)
        s3.download_file(bucket_name, "metadata.json", meta_file)
        logger.info(f"Downloaded existing index for {tenant_id}")
    except Exception as e:
        logger.info(f"No existing index found on MinIO for {tenant_id}: {e}")


def _upload_index(tenant_id: str, index_file: str, meta_file: str):
    """Upload updated FAISS index and metadata to MinIO."""
    bucket_name = f"tenant-{tenant_id}"
    s3 = get_s3_client()
    try:
        s3.upload_file(index_file, bucket_name, "faiss.index")
        s3.upload_file(meta_file, bucket_name, "metadata.json")
        logger.info(f"Uploaded index for {tenant_id} to MinIO")
    except Exception as e:
        logger.error(f"Failed to upload index: {e}")
        raise


def _bump_index_version(tenant_id: str):
    """Increment tenant index version in Redis to invalidate retriever LRU caches."""
    try:
        import redis
        r = redis.Redis.from_url(REDIS_URL, socket_timeout=2.0)
        new_version = r.incr(f"index:version:{tenant_id}")
        r.publish(f"index:updated:{tenant_id}", str(new_version))
        logger.info(f"Bumped index version for tenant {tenant_id} to {new_version}")
    except Exception as e:
        logger.debug(f"Could not bump index version in Redis: {e}")


def _create_index(index_type: str = "Flat", dim: int = EXPECTED_EMBEDDING_DIM):
    """Create a FAISS index based on requested index type."""
    if index_type == "HNSW":
        # HNSW with 32 neighbors per node, inner product metric
        index = faiss.IndexHNSWFlat(dim, 32, faiss.METRIC_INNER_PRODUCT)
        index.hnsw.efSearch = 64
        index.hnsw.efConstruction = 64
        return index
    elif index_type == "IVF-PQ":
        # IVF-PQ: Inverted file with Product Quantization for sub-linear memory
        quantizer = faiss.IndexFlatIP(dim)
        nlist = 100
        m = 64  # 64 bytes per vector (dim 768 / 64 = 12 sub-vectors)
        index = faiss.IndexIVFPQ(quantizer, dim, nlist, m, 8)
        return index
    else:
        # Default Flat inner product (exact cosine after L2 normalization)
        return faiss.IndexFlatIP(dim)


def index_chunks(
    tenant_id: str,
    doc_id: str,
    chunks: list[dict],
    embeddings: list[list[float]],
    switch_threshold: int = None,
    large_index_type: str = None,
):
    """
    Add chunks to the tenant's FAISS index with metadata under distributed lock.
    
    Args:
        tenant_id: Tenant identifier
        doc_id: Document ID being indexed
        chunks: List of {"text": str, "page": int, "chunk_idx": int, ...}
        embeddings: List of embedding vectors (768-dim)
        switch_threshold: Optional override for vector count to auto-switch index type
        large_index_type: Optional override ("HNSW" or "IVF-PQ")
    """
    threshold = switch_threshold or FAISS_SWITCH_THRESHOLD
    target_type = large_index_type or FAISS_LARGE_INDEX_TYPE

    with tenant_index_lock(tenant_id):
        index_file, meta_file = _get_local_paths(tenant_id)
        _download_index(tenant_id, index_file, meta_file)

        # Validate embedding dimensions
        if embeddings:
            actual_dim = len(embeddings[0])
            if actual_dim != EXPECTED_EMBEDDING_DIM:
                raise ValueError(
                    f"Embedding dimension mismatch: expected {EXPECTED_EMBEDDING_DIM}, got {actual_dim}"
                )

        # Load metadata
        metadata = {}
        if os.path.exists(meta_file):
            try:
                with open(meta_file, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
            except Exception as e:
                logger.warning(f"Could not load metadata for {tenant_id}: {e}")
                metadata = {}

        # Normalize new vectors for cosine similarity
        new_vectors = np.array(embeddings, dtype=np.float32)
        if len(new_vectors) > 0:
            faiss.normalize_L2(new_vectors)

        # Initialize or load FAISS index
        if os.path.exists(index_file):
            index = faiss.read_index(index_file)
            logger.info(f"Loaded existing FAISS index with {index.ntotal} vectors")
        else:
            index = _create_index("Flat", EXPECTED_EMBEDDING_DIM)
            logger.info(f"Created new FAISS Flat index (dim={EXPECTED_EMBEDDING_DIM})")

        total_vectors_after = index.ntotal + len(new_vectors)

        # Check if we should auto-switch index type (Flat -> HNSW / IVF-PQ)
        is_flat = isinstance(index, faiss.IndexFlatIP) or type(index).__name__ == "IndexFlatIP"
        if is_flat and total_vectors_after >= threshold and target_type in ("HNSW", "IVF-PQ"):
            logger.info(
                f"[Auto-Switch] Total vectors ({total_vectors_after}) >= threshold ({threshold}). "
                f"Upgrading index to {target_type}!"
            )
            # Reconstruct or rebuild index into target_type
            upgraded_index = _create_index(target_type, EXPECTED_EMBEDDING_DIM)
            
            # Extract existing vectors from Flat index if possible
            existing_vectors = None
            if index.ntotal > 0:
                try:
                    existing_vectors = index.reconstruct_n(0, index.ntotal)
                except Exception as e:
                    logger.warning(f"Could not reconstruct existing vectors: {e}")

            if existing_vectors is not None and len(existing_vectors) > 0:
                all_vectors = np.vstack([existing_vectors, new_vectors])
            else:
                all_vectors = new_vectors

            # Train if needed (IVF-PQ needs training)
            if hasattr(upgraded_index, "is_trained") and not upgraded_index.is_trained:
                logger.info(f"Training {target_type} index on {len(all_vectors)} vectors...")
                upgraded_index.train(all_vectors)

            upgraded_index.add(all_vectors)
            index = upgraded_index
            start_id = total_vectors_after - len(new_vectors)
        else:
            start_id = index.ntotal
            if len(new_vectors) > 0:
                index.add(new_vectors)

        # Store metadata for each newly added chunk
        for i, chunk in enumerate(chunks):
            vector_id = str(start_id + i)
            metadata[vector_id] = {
                "doc_id": doc_id,
                "chunk_idx": chunk.get("chunk_idx", i),
                "page": chunk.get("page", 1),
                "text": chunk.get("text", ""),
            }

        # Save locally
        faiss.write_index(index, index_file)
        with open(meta_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2)

        # Upload to MinIO
        _upload_index(tenant_id, index_file, meta_file)

        # Bump Redis index version
        _bump_index_version(tenant_id)
        logger.info(f"Successfully indexed {len(chunks)} chunks for {tenant_id} (total={index.ntotal})")
