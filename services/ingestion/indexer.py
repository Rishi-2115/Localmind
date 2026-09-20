"""
FAISS indexing with metadata preservation for page-level citations.

Stores chunks with their page numbers, document IDs, and text snippets
for later retrieval and citation generation.
"""
import faiss
import numpy as np
import os
import json
import boto3
import logging

logger = logging.getLogger(__name__)

MINIO_ENDPOINT = os.environ.get("MINIO_ENDPOINT", "minio:9000")
MINIO_ACCESS_KEY = os.environ.get("MINIO_ACCESS_KEY", "minioadmin")
MINIO_SECRET_KEY = os.environ.get("MINIO_SECRET_KEY", "minioadmin")

s3_client = boto3.client(
    's3',
    endpoint_url=f"http://{MINIO_ENDPOINT}",
    aws_access_key_id=MINIO_ACCESS_KEY,
    aws_secret_access_key=MINIO_SECRET_KEY,
)

EXPECTED_EMBEDDING_DIM = 768


def _get_local_paths(tenant_id: str):
    """Get local paths for FAISS index and metadata."""
    base = "/tmp/faiss_indexes"
    os.makedirs(base, exist_ok=True)
    return os.path.join(base, f"{tenant_id}.index"), os.path.join(base, f"{tenant_id}_meta.json")


def _download_index(tenant_id: str, index_file: str, meta_file: str):
    """Download existing FAISS index and metadata from MinIO."""
    bucket_name = f"tenant-{tenant_id}"
    try:
        s3_client.head_bucket(Bucket=bucket_name)
    except Exception:
        logger.info(f"Creating MinIO bucket {bucket_name}")
        s3_client.create_bucket(Bucket=bucket_name)

    try:
        s3_client.download_file(bucket_name, "faiss.index", index_file)
        s3_client.download_file(bucket_name, "metadata.json", meta_file)
        logger.info(f"Downloaded existing index for {tenant_id}")
    except Exception as e:
        logger.info(f"No existing index for {tenant_id}: {e}")
        pass


def _upload_index(tenant_id: str, index_file: str, meta_file: str):
    """Upload updated FAISS index and metadata to MinIO."""
    bucket_name = f"tenant-{tenant_id}"
    try:
        s3_client.upload_file(index_file, bucket_name, "faiss.index")
        s3_client.upload_file(meta_file, bucket_name, "metadata.json")
        logger.info(f"Uploaded index for {tenant_id} to MinIO")
    except Exception as e:
        logger.error(f"Failed to upload index: {e}")
        raise


def index_chunks(
    tenant_id: str,
    doc_id: str,
    chunks: list[dict],
    embeddings: list[list[float]]
):
    """
    Add chunks to the tenant's FAISS index with metadata.
    
    Args:
        tenant_id: Tenant identifier
        doc_id: Document ID being indexed
        chunks: List of {"text": str, "page": int, "chunk_idx": int, ...}
        embeddings: List of embedding vectors (768-dim)
    """
    index_file, meta_file = _get_local_paths(tenant_id)
    _download_index(tenant_id, index_file, meta_file)
    
    # Validate embedding dimensions
    if embeddings:
        actual_dim = len(embeddings[0])
        if actual_dim != EXPECTED_EMBEDDING_DIM:
            raise ValueError(
                f"Embedding dimension mismatch: expected {EXPECTED_EMBEDDING_DIM}, "
                f"got {actual_dim}"
            )
    
    # Initialize or load FAISS index
    if os.path.exists(index_file):
        index = faiss.read_index(index_file)
        logger.info(f"Loaded existing FAISS index with {index.ntotal} vectors")
    else:
        index = faiss.IndexFlatIP(EXPECTED_EMBEDDING_DIM)  # Inner product for cosine similarity
        logger.info(f"Created new FAISS index (dimension={EXPECTED_EMBEDDING_DIM})")
    
    # Load metadata
    metadata = {}
    if os.path.exists(meta_file):
        with open(meta_file, 'r') as f:
            metadata = json.load(f)
    
    # Normalize embeddings for cosine similarity (required for IndexFlatIP)
    vectors = np.array(embeddings, dtype=np.float32)
    faiss.normalize_L2(vectors)
    
    # Add vectors to index
    start_id = index.ntotal
    index.add(vectors)
    logger.info(f"Added {len(vectors)} vectors to index (start_id={start_id})")
    
    # Store metadata for each chunk
    for i, chunk in enumerate(chunks):
        vector_id = str(start_id + i)
        metadata[vector_id] = {
            "doc_id": doc_id,
            "chunk_idx": chunk.get("chunk_idx", i),
            "page": chunk.get("page", 1),  # Page number for citation
            "text": chunk.get("text", ""),  # Store FULL text for LLM context!
        }
    
    # Save locally
    faiss.write_index(index, index_file)
    with open(meta_file, 'w') as f:
        json.dump(metadata, f, indent=2)
    logger.info(f"Saved index and metadata locally for {tenant_id}")
    
    # Upload to MinIO
    _upload_index(tenant_id, index_file, meta_file)
    logger.info(f"Successfully indexed {len(chunks)} chunks from doc {doc_id} for {tenant_id}")
