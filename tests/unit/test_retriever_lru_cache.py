import os
import json
import numpy as np
import faiss
import asyncio
import tempfile
from ml.retrieval.retriever import Retriever, IndexLRUCache


def test_index_lru_cache_basic():
    cache = IndexLRUCache(maxsize=2)
    dim = 2
    idx1 = faiss.IndexFlatIP(dim)
    meta1 = {"0": {"doc_id": "doc1"}}
    idx2 = faiss.IndexFlatIP(dim)
    meta2 = {"0": {"doc_id": "doc2"}}
    idx3 = faiss.IndexFlatIP(dim)
    meta3 = {"0": {"doc_id": "doc3"}}

    # Put tenant-A, tenant-B
    cache.put("tenant-A", "1", idx1, meta1)
    cache.put("tenant-B", "1", idx2, meta2)

    assert cache.get("tenant-A", "1") == (idx1, meta1)
    assert cache.get("tenant-B", "1") == (idx2, meta2)
    assert cache.get("tenant-A", "2") is None  # Different version -> miss

    # Put tenant-C -> exceeds maxsize 2, evicts oldest (tenant-A since tenant-B was accessed last)
    cache.put("tenant-C", "1", idx3, meta3)
    assert cache.get("tenant-C", "1") == (idx3, meta3)
    assert cache.get("tenant-B", "1") == (idx2, meta2)
    assert cache.get("tenant-A", "1") is None  # Evicted

    # Invalidate tenant-B
    cache.invalidate("tenant-B")
    assert cache.get("tenant-B", "1") is None


import pytest


def test_retriever_in_process_cache_hit_and_invalidation():
    tmp_dir = tempfile.mkdtemp()
    retriever = Retriever(cache_maxsize=4)
    retriever.local_index_path = tmp_dir
    tenant_id = "test_lawfirm"

    # Create initial index on disk
    dim = 2
    index = faiss.IndexFlatIP(dim)
    vectors = np.array([[1.0, 0.0]], dtype=np.float32)
    faiss.normalize_L2(vectors)
    index.add(vectors)
    index_path = retriever._get_tenant_index_path(tenant_id)
    faiss.write_index(index, index_path)

    meta_path = retriever._get_tenant_metadata_path(tenant_id)
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump({"0": {"doc_id": "v1_doc", "text": "Version 1 text"}}, f)

    # Put initial version 1 in cache
    retriever.cache.put(tenant_id, "v1", index, {"0": {"doc_id": "v1_doc"}})

    # Cache hit returns v1
    cached = retriever.cache.get(tenant_id, "v1")
    assert cached is not None
    assert cached[1]["0"]["doc_id"] == "v1_doc"

    # Invalidate cache for tenant_id (as indexer does on re-index)
    retriever.cache.invalidate(tenant_id)
    assert retriever.cache.get(tenant_id, "v1") is None

    # Load version 2 into cache
    index2 = faiss.IndexFlatIP(dim)
    vectors2 = np.array([[0.0, 1.0]], dtype=np.float32)
    index2.add(vectors2)
    retriever.cache.put(tenant_id, "v2", index2, {"0": {"doc_id": "v2_doc"}})

    # Verify v2 is returned
    cached_v2 = retriever.cache.get(tenant_id, "v2")
    assert cached_v2 is not None
    assert cached_v2[1]["0"]["doc_id"] == "v2_doc"
