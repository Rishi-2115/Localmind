"""
RAG Quality Test 2: Hallucination Refusal

Verifies that the legal prompt template instructs the LLM to refuse
when context is absent or irrelevant, rather than hallucinating an answer.

We test this at the PROMPT level (not by calling the LLM) because:
  - LLM hallucination refusal is non-deterministic for generative models.
  - The prompt's REFUSAL INSTRUCTION is the mechanism that enforces this.
  - If the instruction is absent or malformed, the LLM will hallucinate.

Tests:
  1. The LEGAL_QA_PROMPT contains explicit refusal instructions.
  2. Empty context produces a prompt that will trigger refusal.
  3. Off-topic context produces a prompt with a mismatch signal.
  4. The context assembly from retrieved chunks is not silently empty.
  5. Verify the "not in context" phrase is present (what the LLM should say).
"""

import pytest
import sys
import os

from helpers import retrieve_from_index, build_context_prompt
from prompts.legal import LEGAL_QA_PROMPT


class TestHallucinationRefusal:
    """
    Tests that the prompt template and pipeline are configured to
    minimize hallucination via explicit refusal instructions.
    """

    def test_prompt_contains_refusal_instruction(self):
        """
        The LEGAL_QA_PROMPT must contain an explicit refusal instruction.
        Without this, the LLM defaults to generating plausible-sounding but
        potentially fabricated legal answers.
        """
        assert "does not contain the answer" in LEGAL_QA_PROMPT.lower() or \
               "not contained in the context" in LEGAL_QA_PROMPT.lower(), (
            "LEGAL_QA_PROMPT is missing a refusal instruction for questions "
            "not answerable from context. Add: "
            "'If the answer is not contained in the context, explicitly state "
            "\"The provided context does not contain the answer to this query.\"'"
        )

    def test_prompt_contains_domain_refusal(self):
        """
        The prompt must instruct the LLM to refuse non-legal questions
        (e.g., 'What is the capital of France?').
        """
        off_topic_signals = [
            "not related to the legal domain",
            "unrelated to the legal",
            "specialized in legal analysis",
            "only assist with queries related",
        ]
        has_domain_refusal = any(
            signal.lower() in LEGAL_QA_PROMPT.lower()
            for signal in off_topic_signals
        )
        assert has_domain_refusal, (
            "LEGAL_QA_PROMPT lacks a domain-scope refusal instruction. "
            "Without this, the LLM will answer questions like 'write me a poem' "
            "inside a law firm's copilot. "
            f"Expected one of: {off_topic_signals}"
        )

    def test_prompt_instructs_no_invented_facts(self):
        """
        The prompt must tell the LLM not to invent facts, precedents, or case law.
        """
        no_invent_signals = [
            "do not invent",
            "must only use the provided context",
            "only use the provided",
            "do not fabricate",
        ]
        has_no_invent = any(
            signal.lower() in LEGAL_QA_PROMPT.lower()
            for signal in no_invent_signals
        )
        assert has_no_invent, (
            "LEGAL_QA_PROMPT does not instruct the LLM to avoid inventing facts. "
            f"Expected one of: {no_invent_signals}"
        )

    def test_empty_context_prompt_contains_refusal_trigger(self):
        """
        When no documents are retrieved, the context is empty.
        The resulting prompt should still contain the refusal instruction
        so the LLM refuses rather than hallucinating.
        """
        empty_context = ""
        prompt = LEGAL_QA_PROMPT.format(
            context=empty_context,
            question="What is the liability cap in the agreement?",
        )
        # The prompt with empty context should still have refusal language
        assert "does not contain the answer" in prompt.lower() or \
               "not contained in the context" in prompt.lower(), (
            "When context is empty, the formatted prompt should still carry "
            "the refusal instruction text. This is what triggers the LLM to "
            "say 'I cannot find this in the documents' rather than hallucinate."
        )

    def test_off_topic_question_prompt_includes_domain_refusal(self):
        """
        When the user asks an off-topic question, the prompt's domain-refusal
        instruction must be present in the formatted string.
        """
        context = "This is a legal service agreement between parties."
        off_topic_question = "What is the recipe for biryani?"
        prompt = LEGAL_QA_PROMPT.format(context=context, question=off_topic_question)

        off_topic_signals = [
            "not related to the legal domain",
            "unrelated to the legal",
            "specialized in legal analysis",
            "only assist with queries related",
        ]
        has_signal = any(sig.lower() in prompt.lower() for sig in off_topic_signals)
        assert has_signal, (
            "Formatted prompt for off-topic question should still carry "
            "the domain-scope refusal instruction. "
            f"Off-topic question was: '{off_topic_question}'"
        )

    def test_retrieved_context_is_not_empty_for_relevant_query(self, rag_index):
        """
        For a question clearly answerable from the fixture, retrieved context
        must not be empty. Empty context → guaranteed hallucination trigger.
        """
        index, metadata_map = rag_index
        question = "What is the total contract value?"
        results = retrieve_from_index(index, metadata_map, question, top_k=3)

        assert len(results) > 0, (
            "For a clear, on-topic question about contract value, retrieval "
            "returned zero chunks. This means the LLM will see empty context "
            "and is likely to hallucinate or refuse incorrectly."
        )

        context = build_context_prompt(results)
        assert len(context.strip()) > 50, (
            f"Assembled context is too short ({len(context)} chars). "
            "Verify that chunks contain meaningful text."
        )

    def test_prompt_citation_format_instruction_present(self):
        """
        The prompt must instruct the LLM to cite [Document, Page] when answering.
        Without this, the model generates answers without citations.
        """
        citation_signals = [
            "cite the specific document",
            "document.*page",
            "[document",
        ]
        import re
        has_citation = any(
            re.search(signal, LEGAL_QA_PROMPT, re.IGNORECASE)
            for signal in citation_signals
        )
        assert has_citation, (
            "LEGAL_QA_PROMPT does not instruct the LLM to cite document/page. "
            "Law firm users need citations to verify answers against source documents."
        )
