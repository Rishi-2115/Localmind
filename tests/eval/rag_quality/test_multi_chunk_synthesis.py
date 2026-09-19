"""
RAG Quality Test 3: Multi-Chunk Synthesis

Verifies that when a question requires information from multiple pages/sections,
the retrieval pipeline:
  1. Returns chunks from MULTIPLE distinct pages (not just one).
  2. The assembled context contains text from all relevant sections.
  3. The context is assembled in the correct [Document: ..., Page: N] format.
  4. No chunks are silently de-duplicated or lost during assembly.

Multi-chunk synthesis is the hardest RAG capability to get right because it
requires the retriever to fetch complementary chunks and the LLM to synthesize
across them. These tests verify the pipeline is CAPABLE of this — they don't
test the LLM's synthesis quality (which is non-deterministic).

Example multi-hop questions:
  - "What are the payment terms and what happens if payment is late?" (pages 3 + 3)
  - "Who owns the work product and how long must confidentiality be maintained?" (pages 4 + 5)
  - "What is the notice period for termination and what fee applies?" (pages 6 + 6)
  - "Summarize the parties to the agreement and the services being provided." (pages 1 + 2)
"""

import pytest
from helpers import (
    retrieve_from_index,
    build_context_prompt,
    GROUND_TRUTH,
)


class TestMultiChunkSynthesis:
    """
    Tests that multi-clause questions trigger retrieval from multiple chunks
    and that the assembled context covers all needed sections.
    """

    def test_cross_page_query_returns_multiple_chunks(self, rag_index):
        """
        A question spanning pages 4 and 5 (IP ownership + confidentiality)
        must retrieve chunks from at least 2 distinct pages.
        """
        index, metadata_map = rag_index
        question = (
            "Who owns the work product created under this agreement, "
            "and for how long must confidentiality be maintained after termination?"
        )
        results = retrieve_from_index(index, metadata_map, question, top_k=5)

        assert len(results) >= 2, (
            f"Multi-hop query returned only {len(results)} chunk(s). "
            "Need at least 2 chunks to synthesize across pages 4 and 5."
        )

        pages_returned = {r["page"] for r in results}
        assert len(pages_returned) >= 2, (
            f"All {len(results)} retrieved chunks come from the same page: {pages_returned}. "
            "Multi-hop synthesis requires chunks from multiple distinct pages."
        )

    def test_payment_query_covers_payment_and_penalty_sections(self, rag_index):
        """
        A question about payment terms AND late payment penalties should
        retrieve content covering both (both are on page 3, different clauses).
        """
        index, metadata_map = rag_index
        question = (
            "What is the payment schedule and what interest rate applies to late payments?"
        )
        results = retrieve_from_index(index, metadata_map, question, top_k=5)
        combined_text = " ".join(r["text"].lower() for r in results)

        # Should find both payment schedule keywords and penalty keyword
        has_schedule = any(
            kw in combined_text
            for kw in ["milestone", "payable", "payment schedule"]
        )
        has_penalty = any(
            kw in combined_text
            for kw in ["eighteen percent", "18%", "interest", "overdue"]
        )

        assert has_schedule, (
            "Combined retrieved context doesn't contain payment schedule information. "
            f"Searched {len(results)} chunks."
        )
        assert has_penalty, (
            "Combined retrieved context doesn't contain late payment penalty information. "
            f"Searched {len(results)} chunks."
        )

    def test_context_contains_all_retrieved_chunks(self, rag_index):
        """
        Every chunk returned by retrieval must appear in the assembled context.
        Silent deduplication or truncation means the LLM misses information.
        """
        index, metadata_map = rag_index
        question = "Explain the intellectual property and confidentiality provisions."
        results = retrieve_from_index(index, metadata_map, question, top_k=5)
        context = build_context_prompt(results)

        for i, doc in enumerate(results):
            # The first 50 characters of each chunk's text should appear in context
            snippet = doc["text"][:50].strip()
            assert snippet in context, (
                f"Chunk {i} (page {doc['page']}) is missing from assembled context. "
                f"Missing snippet: '{snippet}'\n"
                f"Context preview: {context[:400]}"
            )

    def test_context_blocks_ordered_with_doc_headers(self, rag_index):
        """
        Context blocks must be separated and each preceded by a
        [Document: ..., Page: N] header — this is what the LLM uses for citations.
        """
        index, metadata_map = rag_index
        question = "What are the parties to this agreement and what services are covered?"
        results = retrieve_from_index(index, metadata_map, question, top_k=3)
        context = build_context_prompt(results)

        # Count headers in context — should have one per chunk
        import re
        headers = re.findall(r"\[Document: .+?, Page: \d+\]", context)
        assert len(headers) == len(results), (
            f"Expected {len(results)} [Document: ..., Page: N] headers in context, "
            f"found {len(headers)}.\nContext:\n{context[:600]}"
        )

    def test_no_duplicate_chunks_in_context(self, rag_index):
        """
        The same chunk text should not appear more than once in the context.
        Duplicates inflate the context window and can bias the LLM.
        """
        index, metadata_map = rag_index
        question = "Summarize all key provisions of this service agreement."
        results = retrieve_from_index(index, metadata_map, question, top_k=5)

        seen_texts = set()
        for doc in results:
            # Use first 100 chars as dedup key (chunk_idx alone isn't enough across docs)
            key = doc["text"][:100].strip()
            assert key not in seen_texts, (
                f"Duplicate chunk detected in retrieval results.\n"
                f"Text: '{key[:80]}...' appears more than once."
            )
            seen_texts.add(key)

    def test_parties_query_retrieves_page_one_content(self, rag_index):
        """
        A question about the parties to the agreement should retrieve
        content from page 1 (where the parties are defined).
        """
        index, metadata_map = rag_index
        question = "Who are the parties to this service agreement and where are they located?"
        results = retrieve_from_index(index, metadata_map, question, top_k=5)

        pages = [r["page"] for r in results]
        assert 1 in pages, (
            f"Page 1 (party definitions) was not retrieved for a question about parties. "
            f"Pages retrieved: {pages}. "
            "Check that page 1 content is properly indexed."
        )

        # Must contain party names
        combined_text = " ".join(r["text"].lower() for r in results)
        has_client = "sharma" in combined_text or "client" in combined_text
        has_provider = "techsolve" in combined_text or "service provider" in combined_text
        assert has_client and has_provider, (
            f"Retrieved chunks don't mention both parties.\n"
            f"Has client info: {has_client}, Has provider info: {has_provider}\n"
            f"Combined text preview: {combined_text[:300]}"
        )

    def test_top_k_retrieval_diversity(self, rag_index, fixture_pages):
        """
        With top_k=5 and a broad question, retrieved chunks should come from
        at least 3 distinct pages — not all from the same page.
        A high-diversity retrieval means the index captures the full document.
        """
        index, metadata_map = rag_index
        question = (
            "What are the key provisions of this agreement regarding "
            "payment, intellectual property, confidentiality, and termination?"
        )
        results = retrieve_from_index(index, metadata_map, question, top_k=5)
        distinct_pages = {r["page"] for r in results}

        assert len(distinct_pages) >= 3, (
            f"Broad multi-topic query only retrieved chunks from {len(distinct_pages)} page(s): "
            f"{distinct_pages}. Expected at least 3 distinct pages for diversity. "
            "This may indicate the index is over-indexing on one section."
        )
