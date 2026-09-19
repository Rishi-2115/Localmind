"""
RAG Quality Evaluation Harness — conftest.py

Pytest fixtures for all RAG quality tests.
Helper functions live in helpers.py (importable module).
This file provides session-scoped fixtures that build the in-memory index once.

Running:
    pytest tests/eval/rag_quality/ -v
"""

import sys
import os
import pytest

# ── Ensure the rag_quality dir is on sys.path so helpers.py is importable ──
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
if _THIS_DIR not in sys.path:
    sys.path.insert(0, _THIS_DIR)

# ── Also ensure the ingestion service path is available for chunker import ──
_REPO_ROOT = os.path.abspath(os.path.join(_THIS_DIR, "..", "..", ".."))
_INGESTION_PATH = os.path.join(_REPO_ROOT, "services", "ingestion")
_ML_PATH = os.path.join(_REPO_ROOT, "ml")

for _p in [_REPO_ROOT, _INGESTION_PATH, _ML_PATH]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

from helpers import (
    parse_fixture_pages,
    build_in_memory_index,
    GROUND_TRUTH,
    SAMPLE_CONTRACT_PATH,
)


@pytest.fixture(scope="session")
def fixture_pages():
    """Returns the parsed list of pages from sample_contract.txt."""
    pages = parse_fixture_pages()
    assert len(pages) > 0, "Fixture file could not be parsed — check sample_contract.txt"
    return pages


@pytest.fixture(scope="session")
def rag_index(fixture_pages):
    """
    Builds and returns an in-memory FAISS index + metadata map
    from the fixture contract. Session-scoped so it's built once.
    Returns: (faiss.Index, dict[str, dict])
    """
    index, metadata_map = build_in_memory_index(fixture_pages)
    return index, metadata_map


@pytest.fixture(scope="session")
def ground_truth():
    """Returns the ground truth dictionary for the sample contract."""
    return GROUND_TRUTH
