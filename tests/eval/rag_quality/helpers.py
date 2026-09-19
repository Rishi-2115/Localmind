"""
RAG Quality Evaluation Harness — helpers.py

Shared utilities for all RAG quality tests.
This module contains the test helpers that are explicitly imported
by test files. Pytest fixtures live in conftest.py.

Why separate from conftest.py:
    pytest treats conftest.py specially — you cannot `import conftest`
    from test files. Helper functions that test files need to import
    directly must live in a regular Python module like this one.
"""

import os
import sys
import json
import numpy as np
import faiss

# ── Path setup so we can import from the monorepo without installation ──
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
INGESTION_PATH = os.path.join(REPO_ROOT, "services", "ingestion")
ML_PATH = os.path.join(REPO_ROOT, "ml")
API_PATH = os.path.join(REPO_ROOT, "services", "api")

for p in [REPO_ROOT, INGESTION_PATH, ML_PATH, API_PATH]:
    if p not in sys.path:
        sys.path.insert(0, p)

# ── Fixture path ─────────────────────────────────────────────────────────
FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")
SAMPLE_CONTRACT_PATH = os.path.join(FIXTURES_DIR, "sample_contract.txt")

# ── Known ground-truth facts for the sample contract ────────────────────
# These are verified facts embedded in sample_contract.txt at specific pages.
GROUND_TRUTH = {
    "contract_value": {
        "answer_keywords": ["45,00,000", "45 lakhs", "forty-five lakhs"],
        "page": 3,
        "question": "What is the total contract value mentioned in the service agreement?",
    },
    "agreement_term": {
        "answer_keywords": ["twenty-four", "24 months", "24-month"],
        "page": 2,
        "question": "What is the initial term of the agreement?",
    },
    "ip_ownership": {
        "answer_keywords": ["client", "exclusive property", "full payment"],
        "page": 4,
        "question": "Who owns the work product created under this agreement?",
    },
    "confidentiality_survival": {
        "answer_keywords": ["five", "5 years"],
        "page": 5,
        "question": "For how long do confidentiality obligations survive after termination?",
    },
    "termination_convenience_notice": {
        "answer_keywords": ["sixty", "60 days"],
        "page": 6,
        "question": "How many days notice is required for termination for convenience?",
    },
    "late_payment_interest": {
        "answer_keywords": ["eighteen", "18%", "eighteen percent"],
        "page": 3,
        "question": "What is the interest rate charged on late payments?",
    },
}

# ── Page parsing helper ───────────────────────────────────────────────────
def parse_fixture_pages(path: str = SAMPLE_CONTRACT_PATH) -> list:
    """
    Parse the fixture text file into a list of page dicts.
    Each page dict: {"page": int, "text": str}

    The fixture uses === PAGE N === markers to delimit pages.
    """
    pages = []
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    current_page = None
    current_text = []

    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("=== PAGE") and stripped.endswith("==="):
            # Save previous page
            if current_page is not None:
                pages.append({
                    "page": current_page,
                    "text": "\n".join(current_text).strip(),
                })
            # Start new page
            try:
                current_page = int(stripped.split("PAGE")[1].split("===")[0].strip())
            except (ValueError, IndexError):
                current_page = len(pages) + 1
            current_text = []
        else:
            current_text.append(line)

    # Flush final page
    if current_page is not None and current_text:
        pages.append({
            "page": current_page,
            "text": "\n".join(current_text).strip(),
        })

    return pages


# ── Deterministic fake embedder ───────────────────────────────────────────
EMBEDDING_DIM = 768


import hashlib
import re

def _fake_embed(text: str) -> np.ndarray:
    """
    Produce a deterministic 768-dim embedding from text using stable token hashing.
    
    This is NOT a semantic embedding — it exists so the eval harness can
    build a real FAISS index and run retrieval logic without Ollama running.
    Tests run offline with no external service dependency.
    """
    vec = np.zeros(EMBEDDING_DIM, dtype=np.float32)
    tokens = re.findall(r'\b[a-zA-Z0-9%]+\b', text.lower())
    for token in tokens:
        h = int(hashlib.md5(token.encode()).hexdigest(), 16) % EMBEDDING_DIM
        vec[h] += 2.0
        for suffix in ['ing', 'ments', 'ment', 'ed', 'es', 's']:
            if token.endswith(suffix) and len(token) > len(suffix) + 2:
                stem = token[:-len(suffix)]
                h_stem = int(hashlib.md5(stem.encode()).hexdigest(), 16) % EMBEDDING_DIM
                vec[h_stem] += 1.0
                break
    norm = np.linalg.norm(vec)
    if norm > 0:
        vec = vec / norm
    return vec



# ── In-memory FAISS index builder ────────────────────────────────────────
def build_in_memory_index(pages: list) -> tuple:
    """
    Build a real FAISS inner-product index from fixture pages.
    
    Returns:
        (index, metadata_map)
        metadata_map: {str(idx): {"doc_id": ..., "page": ..., "text": ...}}
    """
    from chunker import chunk_text

    index = faiss.IndexFlatIP(EMBEDDING_DIM)
    metadata_map = {}
    global_idx = 0
    doc_id = "sample-contract-001"

    for page_info in pages:
        page_chunks = chunk_text(
            page_info["text"],
            metadata={"doc_id": doc_id, "page": page_info["page"]},
            chunk_size=200,
            overlap=20,
        )
        for chunk in page_chunks:
            emb = _fake_embed(chunk["text"])
            emb_2d = emb.reshape(1, -1)
            faiss.normalize_L2(emb_2d)
            index.add(emb_2d)
            metadata_map[str(global_idx)] = {
                "doc_id": doc_id,
                "page": chunk["page"],
                "text": chunk["text"],
                "chunk_idx": chunk["chunk_idx"],
            }
            global_idx += 1

    return index, metadata_map


# ── Retrieval function (mirrors retriever.py but in-memory) ───────────────
def retrieve_from_index(
    index: faiss.Index,
    metadata_map: dict,
    query: str,
    top_k: int = 3,
) -> list:
    """
    Retrieve top-k chunks from the in-memory FAISS index for a query.
    Mirrors the retrieval logic in ml/retrieval/retriever.py.
    """
    query_vec = _fake_embed(query).reshape(1, -1)
    faiss.normalize_L2(query_vec)
    distances, indices = index.search(query_vec, top_k)
    results = []
    for idx in indices[0]:
        if idx != -1 and str(idx) in metadata_map:
            results.append(metadata_map[str(idx)])
    return results


# ── Context builder (mirrors query.py context assembly) ──────────────────
def build_context_prompt(retrieved_docs: list) -> str:
    """
    Assembles retrieved chunks into the same context string format
    that query.py sends to the LLM.

    Format: --- [Document: {doc_id}, Page: {page}] ---\n{text}
    """
    context_blocks = []
    for i, doc in enumerate(retrieved_docs):
        p = doc.get("page", 1)
        d_id = doc.get("doc_id", f"Doc-{i+1}")
        context_blocks.append(f"--- [Document: {d_id}, Page: {p}] ---\n{doc.get('text', '')}")
    return "\n\n".join(context_blocks)
