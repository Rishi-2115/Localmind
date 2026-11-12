import os
import tempfile
import threading
import json
import faiss
import numpy as np
from unittest.mock import patch
from services.ingestion.indexer import index_chunks, _get_local_paths, EXPECTED_EMBEDDING_DIM


def test_concurrent_ingestion_no_vectors_lost():
    """
    Simulate multiple workers ingesting documents for the SAME tenant simultaneously.
    Asserts distributed/thread locking prevents race conditions and zero vectors are lost.
    """
    tmp_dir = tempfile.mkdtemp()
    tenant_id = "concurrent_tenant_test"

    # Patch local_paths and S3 download/upload to use our temp dir directly
    def mock_local_paths(tid):
        return os.path.join(tmp_dir, f"{tid}.index"), os.path.join(tmp_dir, f"{tid}_meta.json")

    num_workers = 3
    chunks_per_worker = 10
    errors = []

    def worker_task(worker_id):
        try:
            chunks = [
                {"chunk_idx": i, "page": 1, "text": f"Worker {worker_id} chunk {i}"}
                for i in range(chunks_per_worker)
            ]
            # Unique deterministic embedding vector per chunk
            embeddings = [
                [float(worker_id * 10 + i) / 100.0] * EXPECTED_EMBEDDING_DIM
                for i in range(chunks_per_worker)
            ]
            index_chunks(
                tenant_id=tenant_id,
                doc_id=f"doc_w{worker_id}",
                chunks=chunks,
                embeddings=embeddings,
                switch_threshold=1000,  # keep Flat
            )
        except Exception as e:
            errors.append(e)

    threads = []
    with patch("services.ingestion.indexer._get_local_paths", side_effect=mock_local_paths), \
         patch("services.ingestion.indexer._download_index"), \
         patch("services.ingestion.indexer._upload_index"), \
         patch("services.ingestion.indexer._bump_index_version"):

        for w in range(num_workers):
            t = threading.Thread(target=worker_task, args=(w,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

    assert len(errors) == 0, f"Worker errors encountered: {errors}"

    # Verify total vectors in final index matches num_workers * chunks_per_worker exactly
    final_index_file = os.path.join(tmp_dir, f"{tenant_id}.index")
    final_meta_file = os.path.join(tmp_dir, f"{tenant_id}_meta.json")

    assert os.path.exists(final_index_file), "Final index file was not created"
    assert os.path.exists(final_meta_file), "Final metadata file was not created"

    index = faiss.read_index(final_index_file)
    expected_total = num_workers * chunks_per_worker
    assert index.ntotal == expected_total, f"Expected {expected_total} vectors, got {index.ntotal} (lost vectors!)"

    with open(final_meta_file, "r", encoding="utf-8") as f:
        metadata = json.load(f)
    assert len(metadata) == expected_total, f"Expected {expected_total} metadata entries, got {len(metadata)}"


def test_auto_switch_to_hnsw_above_threshold():
    """
    Test that when total vectors exceed switch_threshold, index is converted to HNSW.
    """
    tmp_dir = tempfile.mkdtemp()
    tenant_id = "autoswitch_tenant_test"

    def mock_local_paths(tid):
        return os.path.join(tmp_dir, f"{tid}.index"), os.path.join(tmp_dir, f"{tid}_meta.json")

    chunks1 = [{"chunk_idx": i, "page": 1, "text": f"Initial chunk {i}"} for i in range(5)]
    embeddings1 = [[0.1] * EXPECTED_EMBEDDING_DIM for _ in range(5)]

    chunks2 = [{"chunk_idx": i, "page": 1, "text": f"Threshold crossing chunk {i}"} for i in range(6)]
    embeddings2 = [[0.2] * EXPECTED_EMBEDDING_DIM for _ in range(6)]

    with patch("services.ingestion.indexer._get_local_paths", side_effect=mock_local_paths), \
         patch("services.ingestion.indexer._download_index"), \
         patch("services.ingestion.indexer._upload_index"), \
         patch("services.ingestion.indexer._bump_index_version"):

        # First batch (5 vectors) with threshold 10 -> stays Flat
        index_chunks(tenant_id, "doc1", chunks1, embeddings1, switch_threshold=10, large_index_type="HNSW")
        index_file = os.path.join(tmp_dir, f"{tenant_id}.index")
        idx1 = faiss.read_index(index_file)
        assert idx1.ntotal == 5
        assert isinstance(idx1, faiss.IndexFlatIP)

        # Second batch (+6 vectors -> 11 total) >= threshold 10 -> auto-switches to HNSW!
        index_chunks(tenant_id, "doc2", chunks2, embeddings2, switch_threshold=10, large_index_type="HNSW")
        idx2 = faiss.read_index(index_file)
        assert idx2.ntotal == 11
        assert isinstance(idx2, faiss.IndexHNSWFlat)

