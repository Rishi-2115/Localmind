"""
Live Ollama Integration Test Suite

This test suite executes real end-to-end inference against a running Ollama instance
(by default http://localhost:11434) to verify:
  1. Real Citation Accuracy: The LLM includes explicit document & page citations when answering fact queries.
  2. Real Hallucination Refusal: The LLM explicitly refuses when a question cannot be answered from the provided context.
  3. Real Domain Refusal: The LLM refuses to answer off-topic queries outside the legal document domain.
  4. Real Multi-Chunk Synthesis: The LLM synthesizes facts across disparate pages (e.g. fee calculation from Page 3 + Page 6).

If Ollama is not accessible or the model is not installed, tests are marked as skipped.
"""

import os
import pytest
import httpx
from ml.prompts.legal import LEGAL_QA_PROMPT

OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
TEST_MODEL = os.environ.get("LOCALMIND_TEST_MODEL", "llama3.2:3b")


def is_ollama_ready() -> bool:
    """Check if Ollama server is reachable and TEST_MODEL is pulled."""
    try:
        res = httpx.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=3.0)
        if res.status_code != 200:
            return False
        models = [m["name"].split(":")[0] for m in res.json().get("models", [])]
        target = TEST_MODEL.split(":")[0]
        return target in models
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not is_ollama_ready(),
    reason=f"Ollama not running at {OLLAMA_BASE_URL} or {TEST_MODEL} not downloaded.",
)


def call_ollama(prompt: str, timeout: float = 60.0) -> str:
    """Send a prompt to the live Ollama generate API and return raw response string."""
    response = httpx.post(
        f"{OLLAMA_BASE_URL}/api/generate",
        json={
            "model": TEST_MODEL,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.0},
        },
        timeout=timeout,
    )
    assert response.status_code == 200, f"Ollama returned {response.status_code}: {response.text}"
    return response.json().get("response", "").strip()


class TestLiveOllamaRAG:

    def test_live_ollama_page_specific_citation(self):
        """
        Verify that given a context with [Document: sample_contract.txt, Page: 3],
        the LLM extracts the correct value (INR 45,00,000) and explicitly cites Page 3.
        """
        context = (
            "--- [Document: sample_contract.txt, Page: 3] ---\n"
            "3.1 Total Contract Value: The total fee payable under this Agreement is INR 45,00,000/- "
            "(Rupees Forty-Five Lakhs only) payable in installments upon achievement of Milestones.\n"
            "3.2 Payment Schedule: Milestone 1: INR 15,00,000 upon contract signing."
        )
        question = "What is the total contract value specified in the agreement?"
        prompt = LEGAL_QA_PROMPT.format(context=context, question=question)

        answer = call_ollama(prompt)

        # 1. Must state the actual fact
        assert any(kw in answer for kw in ["45,00,000", "45 Lakhs", "45 lakhs", "Forty-Five Lakhs"]), (
            f"Expected contract value (45,00,000) not found in answer:\n{answer}"
        )

        # 2. Must cite Page 3
        assert "page 3" in answer.lower() or "page: 3" in answer.lower(), (
            f"Expected citation to Page 3 missing in answer:\n{answer}"
        )

    def test_live_ollama_hallucination_refusal_unanswerable(self):
        """
        Verify that when asked a question whose answer is NOT in the context,
        the LLM does not invent information, but states it does not contain the answer.
        """
        context = (
            "--- [Document: sample_contract.txt, Page: 3] ---\n"
            "3.1 Total Contract Value: The total fee payable under this Agreement is INR 45,00,000/-.\n"
            "3.2 Payment Schedule: Milestone 1: INR 15,00,000 upon contract signing."
        )
        question = "What is the penalty for failure to comply with the European GDPR regulations?"
        prompt = LEGAL_QA_PROMPT.format(context=context, question=question)

        answer = call_ollama(prompt)

        # Must trigger refusal / unanswerable phrasing
        refusal_indicators = [
            "does not contain",
            "not contained",
            "not mentioned",
            "no information",
            "unable to find",
            "does not provide",
            "not specified",
        ]
        assert any(ind in answer.lower() for ind in refusal_indicators), (
            f"LLM did not refuse unanswerable question. Answer:\n{answer}"
        )

    def test_live_ollama_domain_refusal_off_topic(self):
        """
        Verify that off-topic requests (e.g. non-legal queries) are refused.
        """
        context = "--- [Document: sample_contract.txt, Page: 1] ---\nLegal Service Agreement"
        question = "How do I bake a chocolate cake from scratch?"
        prompt = LEGAL_QA_PROMPT.format(context=context, question=question)

        answer = call_ollama(prompt)

        domain_refusal_indicators = [
            "unable to provide assistance",
            "cannot assist",
            "specialized in legal",
            "only assist with queries related to",
            "only assist with legal",
            "unrelated to the legal",
            "i am unable to",
        ]
        assert any(ind in answer.lower() for ind in domain_refusal_indicators), (
            f"LLM did not refuse off-topic prompt. Answer:\n{answer}"
        )

    def test_live_ollama_cross_section_synthesis(self):
        """
        Verify synthesis across multiple chunks:
        Page 3 gives Contract Value (INR 45,00,000).
        Page 6 gives Termination fee (20% of remaining unpaid contract value).
        """
        context = (
            "--- [Document: sample_contract.txt, Page: 3] ---\n"
            "3.1 Total Contract Value: The total fee payable under this Agreement is INR 45,00,000/- "
            "(Rupees Forty-Five Lakhs only).\n\n"
            "--- [Document: sample_contract.txt, Page: 6] ---\n"
            "7.2 The Client may terminate this Agreement for convenience upon sixty (60) days written notice.\n"
            "7.3 Upon termination for convenience by the Client, the Client shall pay the Service Provider "
            "for all Services satisfactorily performed, plus a termination fee equal to twenty percent (20%) "
            "of the remaining unpaid Contract Value."
        )
        question = "What are the financial implications and fees if the Client terminates for convenience?"
        prompt = LEGAL_QA_PROMPT.format(context=context, question=question)

        answer = call_ollama(prompt)

        # Must capture both aspects (20% termination fee AND reference to contract value or both sections)
        assert "20%" in answer or "twenty percent" in answer.lower(), (
            f"Missing 20% termination fee in synthesis:\n{answer}"
        )
        assert any(kw in answer for kw in ["45,00,000", "Contract Value", "contract value", "3.1", "7.3"]), (
            f"Failed cross-section synthesis between Page 3 and Page 6:\n{answer}"
        )
