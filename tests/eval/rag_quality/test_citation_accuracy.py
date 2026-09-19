"""
RAG Quality Test 1: Citation Accuracy

Verifies that when the pipeline retrieves chunks for a fact-specific question,
the retrieved chunks:
  1. Actually contain the answer text.
  2. Carry the correct page number metadata (not page 1 for everything).
  3. Are surfaced with [Document: ..., Page: N] headers in the assembled context.

This test exercises the pipeline from query → FAISS retrieval → context assembly.
It does NOT call the LLM — it verifies that the RIGHT information reaches the LLM
before generation happens.

Why this matters:
  If page metadata is wrong, citations in the final answer will be wrong
  even if the answer text is correct. Law firm clients will notice.
"""

import pytest
from helpers import (
    retrieve_from_index,
    build_context_prompt,
    GROUND_TRUTH,
)


class TestCitationAccuracy:
    """
    For each ground-truth fact, verify the retrieval pipeline surfaces
    the correct chunk with correct page metadata.
    """

    def test_contract_value_retrieved_with_correct_page(self, rag_index):
        """INR 45,00,000 lives on page 3 — retrieval must surface page 3 chunks."""
        index, metadata_map = rag_index
        gt = GROUND_TRUTH["contract_value"]
        results = retrieve_from_index(index, metadata_map, gt["question"], top_k=5)

        assert len(results) > 0, "Retriever returned no chunks — index may be empty"

        # At least one result must contain the answer keyword
        texts = [r["text"].lower() for r in results]
        found_answer = any(
            any(kw.lower() in t for kw in gt["answer_keywords"])
            for t in texts
        )
        assert found_answer, (
            f"None of the retrieved chunks contain expected keywords {gt['answer_keywords']}.\n"
            f"Retrieved chunks:\n" + "\n---\n".join(t[:200] for t in texts)
        )

        # The chunk containing the answer must have page == 3
        answer_chunk = next(
            (r for r in results if any(kw.lower() in r["text"].lower() for kw in gt["answer_keywords"])),
            None,
        )
        assert answer_chunk is not None
        assert answer_chunk["page"] == gt["page"], (
            f"Answer chunk has wrong page metadata. "
            f"Expected page {gt['page']}, got page {answer_chunk['page']}.\n"
            f"Chunk text: {answer_chunk['text'][:300]}"
        )

    def test_confidentiality_survival_correct_page(self, rag_index):
        """'5 years' confidentiality survival lives on page 5."""
        index, metadata_map = rag_index
        gt = GROUND_TRUTH["confidentiality_survival"]
        results = retrieve_from_index(index, metadata_map, gt["question"], top_k=5)

        assert len(results) > 0, "No chunks retrieved for confidentiality question"

        answer_chunk = next(
            (r for r in results if any(kw.lower() in r["text"].lower() for kw in gt["answer_keywords"])),
            None,
        )
        assert answer_chunk is not None, (
            f"No chunk contains confidentiality survival terms {gt['answer_keywords']}. "
            f"Retrieved: " + str([r["text"][:100] for r in results])
        )
        assert answer_chunk["page"] == gt["page"], (
            f"Expected page {gt['page']}, got {answer_chunk['page']}"
        )

    def test_termination_notice_correct_page(self, rag_index):
        """'60 days notice for termination for convenience' lives on page 6."""
        index, metadata_map = rag_index
        gt = GROUND_TRUTH["termination_convenience_notice"]
        results = retrieve_from_index(index, metadata_map, gt["question"], top_k=5)

        answer_chunk = next(
            (r for r in results if any(kw.lower() in r["text"].lower() for kw in gt["answer_keywords"])),
            None,
        )
        assert answer_chunk is not None, (
            f"No chunk contains termination notice period. "
            f"Retrieved pages: {[r['page'] for r in results]}"
        )
        assert answer_chunk["page"] == gt["page"], (
            f"Expected page {gt['page']}, got {answer_chunk['page']}"
        )

    def test_context_headers_include_doc_and_page(self, rag_index):
        """
        The assembled context string must include [Document: ..., Page: N] headers
        for every retrieved chunk. This is what the LLM sees and cites from.
        """
        index, metadata_map = rag_index
        gt = GROUND_TRUTH["contract_value"]
        results = retrieve_from_index(index, metadata_map, gt["question"], top_k=3)
        context = build_context_prompt(results)

        # Every retrieved chunk must have a header injected
        for doc in results:
            expected_header = f"[Document: {doc['doc_id']}, Page: {doc['page']}]"
            assert expected_header in context, (
                f"Context is missing header '{expected_header}'.\n"
                f"Context preview:\n{context[:500]}"
            )

    def test_no_chunks_have_null_page_metadata(self, rag_index):
        """
        Every chunk in the index must have a non-null, positive-integer page number.
        A page of None or 0 means the chunker lost page tracking.
        """
        _, metadata_map = rag_index
        for idx, meta in metadata_map.items():
            page = meta.get("page")
            assert page is not None, f"Chunk {idx} has None page metadata: {meta}"
            assert isinstance(page, int), f"Chunk {idx} page is not an int: {page!r}"
            assert page >= 1, f"Chunk {idx} has invalid page number {page}"

    def test_multiple_pages_represented_in_index(self, rag_index, fixture_pages):
        """
        The index must contain chunks from multiple pages.
        If all chunks show page=1, page-preservation in the worker is broken.
        """
        _, metadata_map = rag_index
        pages_in_index = {meta["page"] for meta in metadata_map.values()}
        total_fixture_pages = len(fixture_pages)

        assert len(pages_in_index) > 1, (
            f"Index only contains page {pages_in_index}. "
            f"Page metadata is not being preserved — all chunks are labelled page 1."
        )
        # We should have chunks from at least half the fixture pages
        assert len(pages_in_index) >= total_fixture_pages // 2, (
            f"Only {len(pages_in_index)} of {total_fixture_pages} pages represented. "
            f"Pages found: {sorted(pages_in_index)}"
        )

    def test_late_payment_interest_correct_page(self, rag_index):
        """'18% per annum' late payment interest lives on page 3."""
        index, metadata_map = rag_index
        gt = GROUND_TRUTH["late_payment_interest"]
        results = retrieve_from_index(index, metadata_map, gt["question"], top_k=5)

        answer_chunk = next(
            (r for r in results if any(kw.lower() in r["text"].lower() for kw in gt["answer_keywords"])),
            None,
        )
        assert answer_chunk is not None, (
            f"No chunk contains late payment interest rate. "
            f"Checked {len(results)} chunks. Pages: {[r['page'] for r in results]}"
        )
        assert answer_chunk["page"] == gt["page"], (
            f"Expected page {gt['page']}, got {answer_chunk['page']}"
        )
