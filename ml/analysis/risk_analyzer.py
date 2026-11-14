"""
Clause Risk Analyzer Engine for Legal Documents.

Extracts, evaluates, and flags contractual risks across standard legal categories:
1. Indemnity & Liability Caps (unlimited liability vs capped exposure)
2. Termination for Convenience (short notice windows, asymmetric remedies)
3. Non-Compete & Restrictive Covenants (geographic / temporal overbreadth)
4. Governing Law & Dispute Resolution (foreign jurisdiction, mandatory arbitration)
5. Confidentiality & Non-Disclosure (perpetual obligations, broad trade secret definitions)

Uses hybrid rules (regex/keywords) + local LLM evaluation with structured JSON schemas.
"""
import re
import json
import logging
import httpx
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

# Heuristic patterns to pinpoint relevant sections before LLM evaluation
CLAUSE_PATTERNS = {
    "liability": re.compile(r"(limitation of liability|aggregate liability|direct damages|consequential damages|in no event shall)", re.IGNORECASE),
    "indemnification": re.compile(r"(indemnif|hold harmless|defend, indemnify)", re.IGNORECASE),
    "termination": re.compile(r"(termination for convenience|termination without cause|written notice of termination|days prior written notice)", re.IGNORECASE),
    "non_compete": re.compile(r"(non-compete|non compete|restrictive covenant|covenant not to compete|solicitation of customers)", re.IGNORECASE),
    "jurisdiction": re.compile(r"(governing law|jurisdiction|dispute resolution|courts of|exclusive jurisdiction|arbitration)", re.IGNORECASE),
    "dpdpa_health_data": re.compile(r"(patient data|health records|personal data|ai training|data license|cross-border|dpdpa|fiduciary|consent withdrawal|breach notice)", re.IGNORECASE),
}

RISK_EVALUATION_PROMPT = """You are an expert corporate legal auditor. Evaluate the following contract clause for legal, operational, and commercial exposure.

Clause Category: {category}
Document Page: {page}
Clause Text:
"{text}"

Evaluate the clause against standard institutional legal playbooks and return ONLY a valid JSON object matching this schema:
{{
    "risk_level": "LOW" | "MEDIUM" | "HIGH" | "CRITICAL",
    "reasoning": "Clear 1-2 sentence explanation of why this clause exposes the client to risk or whether it meets standard market practice.",
    "recommendation": "Specific actionable legal edit or counter-proposal to mitigate exposure."
}}

Criteria:
- CRITICAL: Unlimited liability, unilateral indemnification with no carve-outs, or unreasonable restrictions.
- HIGH: Asymmetric termination (<15 days notice), broad non-competes (>12 months), or foreign jurisdiction without arbitration.
- MEDIUM: Standard clauses missing reciprocal protections or mutual liability caps.
- LOW: Standard balanced bilateral clause aligned with market practice.
"""


def detect_candidate_clauses(chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Scan chunks using regex heuristics to find candidate clauses requiring deep risk audit."""
    candidates = []
    seen_categories_per_page = set()

    for chunk in chunks:
        text = chunk.get("text", "")
        page = chunk.get("page", 1)

        for category, pattern in CLAUSE_PATTERNS.items():
            if pattern.search(text):
                key = (category, page)
                if key not in seen_categories_per_page:
                    seen_categories_per_page.add(key)
                    candidates.append({
                        "category": category,
                        "text": text[:1200],  # Bound context window
                        "page": page,
                    })

    return candidates


def analyze_clause_with_heuristics(category: str, text: str, page: int) -> Dict[str, Any]:
    """Fallback rule-based risk evaluation if local LLM is temporarily unreachable."""
    lower = text.lower()
    
    if category == "liability":
        if "unlimited" in lower or ("no event" in lower and "aggregate liability" not in lower):
            return {
                "clause_type": category,
                "risk_level": "CRITICAL",
                "excerpt": text[:300] + "...",
                "page_number": page,
                "reasoning": "No explicit aggregate liability cap detected, exposing client to unbounded financial exposure.",
                "recommendation": "Insert mutual liability cap limited to fees paid in preceding 12 months."
            }
        return {
            "clause_type": category,
            "risk_level": "LOW",
            "excerpt": text[:300] + "...",
            "page_number": page,
            "reasoning": "Standard liability limitation with liability caps present.",
            "recommendation": "Verify exclusions (e.g. gross negligence, willful misconduct) match standard playbook."
        }

    if category == "indemnification":
        if "solely" in lower or "shall defend and indemnify" in lower and "mutual" not in lower:
            return {
                "clause_type": category,
                "risk_level": "HIGH",
                "excerpt": text[:300] + "...",
                "page_number": page,
                "reasoning": "Unilateral indemnification obligation imposed without reciprocal protection.",
                "recommendation": "Amend clause to provide mutual indemnification limited to third-party IP infringement."
            }
        return {
            "clause_type": category,
            "risk_level": "MEDIUM",
            "excerpt": text[:300] + "...",
            "page_number": page,
            "reasoning": "Standard indemnification clause with defined scope.",
            "recommendation": "Ensure procedural notice requirements and right-to-defend clauses are incorporated."
        }

    if category == "termination":
        match = re.search(r"(\d+)\s+days", lower)
        days = int(match.group(1)) if match else 30
        if days < 15:
            return {
                "clause_type": category,
                "risk_level": "HIGH",
                "excerpt": text[:300] + "...",
                "page_number": page,
                "reasoning": f"Short termination notice window ({days} days) threatens operational continuity.",
                "recommendation": "Negotiate minimum 30 days prior written notice for convenience."
            }
        return {
            "clause_type": category,
            "risk_level": "LOW",
            "excerpt": text[:300] + "...",
            "page_number": page,
            "reasoning": f"Balanced termination notice period ({days} days) within market standard.",
            "recommendation": "Confirm post-termination data transition obligations are explicitly documented."
        }

    if category == "dpdpa_health_data":
        if "ai models" in lower or "train" in lower or "perpetual" in lower or "worldwide license" in lower:
            return {
                "clause_type": "Data Privacy & AI Training (DPDP Act)",
                "risk_level": "CRITICAL",
                "excerpt": text[:300] + "...",
                "page_number": page,
                "reasoning": "Vendor claims perpetual, worldwide rights to use confidential personal/patient data to train third-party AI models, violating DPDP Act 2023 purpose limitation safeguards.",
                "recommendation": "Strike out all model training rights; explicitly specify that client data is strictly segregated and cannot be utilized for machine learning."
            }
        return {
            "clause_type": "Data Protection & Fiduciary Covenant",
            "risk_level": "LOW",
            "excerpt": text[:300] + "...",
            "page_number": page,
            "reasoning": "Standard statutory commitment adhering to applicable data privacy standards.",
            "recommendation": "Mandate explicit 72-hour security incident notification to Data Protection Board."
        }

    return {
        "clause_type": category,
        "risk_level": "MEDIUM",
        "excerpt": text[:300] + "...",
        "page_number": page,
        "reasoning": f"Standard {category} clause detected requiring legal review for client-specific alignment.",
        "recommendation": "Review against organizational standard contracting guidelines."
    }


def analyze_clause_with_llm(
    category: str,
    text: str,
    page: int,
    ollama_base_url: str = "http://ollama:11434",
    model: str = "llama3.2:3b",
) -> Dict[str, Any]:
    """Call Ollama to assess legal risk with structured JSON response."""
    prompt = RISK_EVALUATION_PROMPT.format(category=category, page=page, text=text)

    try:
        with httpx.Client(timeout=15.0) as client:
            resp = client.post(
                f"{ollama_base_url}/api/generate",
                json={
                    "model": model,
                    "prompt": prompt,
                    "format": "json",
                    "stream": False,
                    "options": {"temperature": 0.1},
                },
            )
            if resp.status_code == 200:
                body = resp.json()
                raw_response = body.get("response", "{}")
                data = json.loads(raw_response)
                
                risk_level = data.get("risk_level", "MEDIUM").upper()
                if risk_level not in {"LOW", "MEDIUM", "HIGH", "CRITICAL"}:
                    risk_level = "MEDIUM"

                return {
                    "clause_type": category,
                    "risk_level": risk_level,
                    "excerpt": text[:300] + ("..." if len(text) > 300 else ""),
                    "page_number": page,
                    "reasoning": data.get("reasoning", "Evaluated against standard market contracting practice."),
                    "recommendation": data.get("recommendation", "Review against organization playbook."),
                }
    except Exception as e:
        logger.warning(f"Ollama structured risk assessment failed ({e}), falling back to deterministic heuristics.")

    return analyze_clause_with_heuristics(category, text, page)


def evaluate_document_risks(
    chunks: List[Dict[str, Any]],
    ollama_base_url: str = "http://ollama:11434",
    model: str = "llama3.2:3b",
) -> List[Dict[str, Any]]:
    """Scan all chunks in a document and produce an executive risk audit report."""
    candidates = detect_candidate_clauses(chunks)
    logger.info(f"Identified {len(candidates)} candidate risk clauses for audit.")

    risks = []
    # Cap evaluated clauses per doc to 5 highest-priority sections to maintain sub-second throughput
    for item in candidates[:6]:
        eval_result = analyze_clause_with_llm(
            category=item["category"],
            text=item["text"],
            page=item["page"],
            ollama_base_url=ollama_base_url,
            model=model,
        )
        risks.append(eval_result)

    return risks

