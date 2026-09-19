import pytest
import os
import json
import numpy as np
import faiss
from ml.retrieval.retriever import Retriever

@pytest.fixture
def mock_faiss_index(tmp_path):
    tenant_id = "test_tenant"
    retriever = Retriever()
    retriever.local_index_path = str(tmp_path)
    
    # Create mock index
    dim = 2
    index = faiss.IndexFlatIP(dim)
    vectors = np.array([[1.0, 0.0], [0.0, 1.0]], dtype=np.float32)
    faiss.normalize_L2(vectors)
    index.add(vectors)
    
    index_path = retriever._get_tenant_index_path(tenant_id)
    faiss.write_index(index, index_path)
    
    # Create mock metadata
    meta_path = retriever._get_tenant_metadata_path(tenant_id)
    with open(meta_path, "w") as f:
        json.dump({
            "0": {"doc_id": "doc1", "text": "chunk 1"},
            "1": {"doc_id": "doc2", "text": "chunk 2"}
        }, f)
        
    return retriever, tenant_id

@pytest.mark.asyncio
async def test_retrieval(mock_faiss_index):
    retriever, tenant_id = mock_faiss_index
    
    # Query matching vector 0
    results = await retriever.retrieve(tenant_id, [1.0, 0.0], top_k=1)
    
    assert len(results) == 1
    assert results[0]["doc_id"] == "doc1"
