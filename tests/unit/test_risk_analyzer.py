import pytest
from ml.analysis.risk_analyzer import (
    detect_candidate_clauses,
    analyze_clause_with_heuristics,
    evaluate_document_risks,
)

def test_detect_candidate_clauses():
    chunks = [
        {
            "text": "The aggregate liability of either party under this agreement shall in no event exceed fees paid in the prior 12 months.",
            "page": 3,
        },
        {
            "text": "Either party may terminate this agreement without cause upon providing 10 days prior written notice.",
            "page": 5,
        },
        {
            "text": "This agreement shall be governed by the laws of England and Wales and the courts of London shall have exclusive jurisdiction.",
            "page": 8,
        },
    ]

    candidates = detect_candidate_clauses(chunks)
    assert len(candidates) >= 3
    categories = {c["category"] for c in candidates}
    assert "liability" in categories
    assert "termination" in categories
    assert "jurisdiction" in categories


def test_analyze_clause_heuristics_liability():
    # Unlimited liability clause
    text = "The vendor shall have unlimited liability for all damages whatsoever arising out of breach."
    risk = analyze_clause_with_heuristics("liability", text, page=2)
    assert risk["risk_level"] == "CRITICAL"
    assert "unbounded financial exposure" in risk["reasoning"]

    # Capped liability clause
    safe_text = "In no event shall aggregate liability exceed the total amounts paid hereunder."
    safe_risk = analyze_clause_with_heuristics("liability", safe_text, page=2)
    assert safe_risk["risk_level"] == "LOW"


def test_analyze_clause_heuristics_termination():
    # 7-day termination notice (high risk)
    text = "Client may terminate this agreement upon 7 days written notice."
    risk = analyze_clause_with_heuristics("termination", text, page=4)
    assert risk["risk_level"] == "HIGH"
    assert "7 days" in risk["reasoning"]

    # 30-day termination notice (standard/low risk)
    safe_text = "Either party may terminate upon 30 days prior written notice."
    safe_risk = analyze_clause_with_heuristics("termination", safe_text, page=4)
    assert safe_risk["risk_level"] == "LOW"


def test_evaluate_document_risks():
    chunks = [
        {
            "text": "Party A solely and unconditionally agrees to defend, indemnify, and hold harmless Party B against all liabilities.",
            "page": 2,
        }
    ]
    # Without live Ollama, fallback heuristics must run and return structured items
    risks = evaluate_document_risks(chunks, ollama_base_url="http://invalid-host:11434")
    assert len(risks) >= 1
    assert risks[0]["clause_type"] == "indemnification"
    assert risks[0]["risk_level"] in {"HIGH", "CRITICAL", "MEDIUM"}
    assert "recommendation" in risks[0]

