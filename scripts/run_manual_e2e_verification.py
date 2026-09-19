"""
Manual End-to-End UI Verification Script using Playwright

Automates:
1. Login with seeded credentials -> 403 PASSWORD_CHANGE_REQUIRED detection.
2. Mandatory password rotation in the UI -> Set new compliant password (LocalMindSecure2027#).
3. Navigation to Documents & Ingest -> Upload sample_contract.pdf -> Wait for 'indexed' state.
4. Navigation to Copilot Chat -> Execute 3 verification queries:
   - Question 1: Page-specific fact (contract value & payment schedule).
   - Question 2: Cross-section synthesis (termination for convenience financial terms).
   - Question 3: Unanswerable question (European GDPR penalty clauses).
5. Captures screenshots to the artifacts directory and prints verbatim model responses.
"""

import os
import sys
import time
from playwright.sync_api import sync_playwright

ARTIFACT_DIR = r"C:\Users\Rishi shukla\.gemini\antigravity-ide\brain\2bea9998-7932-4461-ab2d-02f4060c4482"
FIXTURE_PDF = os.path.join(os.path.dirname(__file__), "..", "tests", "eval", "rag_quality", "fixtures", "sample_contract.pdf")
APP_URL = os.environ.get("APP_URL", "http://localhost:5173")


import subprocess

def run_verification():
    print(f"=== Starting LocalMind Manual UI Verification ===")
    print(f"App URL: {APP_URL}")
    print(f"Fixture PDF: {FIXTURE_PDF}")
    assert os.path.exists(FIXTURE_PDF), f"Fixture PDF does not exist at {FIXTURE_PDF}"

    print("Resetting admin user to fresh unrotated state in Postgres...")
    # Delete FK-dependent rows first to avoid constraint violations from prior runs
    cleanup_sql = (
        "DELETE FROM audit_logs WHERE tenant_id = 'pilot-lawfirm-01'; "
        "DELETE FROM documents WHERE tenant_id = 'pilot-lawfirm-01'; "
        "DELETE FROM users WHERE email = 'admin@localmind.in';"
    )
    subprocess.run(
        ["docker", "exec", "localmind-db-1", "psql", "-U", "user", "-d", "localmind", "-c", cleanup_sql],
        check=True,
    )
    subprocess.run(["docker", "restart", "localmind-api-1"], check=True)
    time.sleep(5)
    print("Database seeded with fresh default credentials.")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1280, "height": 900})
        page = context.new_page()

        # ── Step 1: Open App & Observe Initial Login ─────────────────
        print("\n--- 1. Navigating to Login Page ---")
        page.goto(APP_URL)
        page.wait_for_selector("#login-submit-btn")
        page.screenshot(path=os.path.join(ARTIFACT_DIR, "manual_step1_login_initial.png"))
        print("Captured: manual_step1_login_initial.png")

        # ── Step 2: Attempt Login -> Trigger Password Change ─────────
        print("\n--- 2. Submitting default admin credentials ---")
        page.click("#login-submit-btn")

        page.wait_for_selector("#new-password-input", timeout=10000)
        page.screenshot(path=os.path.join(ARTIFACT_DIR, "manual_step2_password_rotation.png"))
        print("Success: Mandatory password rotation screen displayed!")
        print("Captured: manual_step2_password_rotation.png")

        # ── Step 3: Complete Password Rotation ────────────────────────
        print("\n--- 3. Submitting new strong password (LocalMindSecure2027#) ---")
        page.fill("#new-password-input", "LocalMindSecure2027#")
        page.fill("#confirm-password-input", "LocalMindSecure2027#")
        page.click("#submit-new-password-btn")

        page.wait_for_selector("#nav-docs-btn", timeout=15000)
        page.screenshot(path=os.path.join(ARTIFACT_DIR, "manual_step3_dashboard_entered.png"))
        print("Success: Authenticated and entered dashboard!")
        print("Captured: manual_step3_dashboard_entered.png")

        # ── Step 4: Ingest Fixture Contract ───────────────────────────
        print("\n--- 4. Navigating to Documents & Ingest ---")
        page.click("#nav-docs-btn")
        page.wait_for_selector("#file-upload-input", state="attached")

        print(f"Uploading file: {FIXTURE_PDF}")
        page.set_input_files("#file-upload-input", FIXTURE_PDF)
        page.wait_for_selector("#start-upload-btn")
        page.click("#start-upload-btn")

        print("Waiting for ingestion pipeline to parse, chunk, embed, and index...")
        # Poll table for 'indexed' status
        start_time = time.time()
        indexed = False
        while time.time() - start_time < 120:
            content = page.content()
            if "indexed" in content.lower():
                indexed = True
                break
            print(f"Waiting for indexing... elapsed: {int(time.time() - start_time)}s")
            time.sleep(3)

        assert indexed, "Document ingestion timed out or failed to reach 'indexed' status"
        page.screenshot(path=os.path.join(ARTIFACT_DIR, "manual_step4_document_indexed.png"))
        print("Success: sample_contract.pdf reached status 'indexed'!")
        print("Captured: manual_step4_document_indexed.png")

        # ── Step 5: Ask 3 Verification Questions in Chat ──────────────
        print("\n--- 5. Navigating to Copilot Chat ---")
        page.click("#nav-chat-btn")
        page.wait_for_selector("#chat-query-input")

        questions = [
            (
                "Question 1 (Page-Specific Fact)",
                "What is the total contract value and payment schedule?",
                "manual_step5_q1_contract_value.png",
            ),
            (
                "Question 2 (Cross-Section Synthesis)",
                "What are the financial terms if the Client terminates the agreement for convenience?",
                "manual_step6_q2_synthesis.png",
            ),
            (
                "Question 3 (Unanswerable Question)",
                "What are the penalty clauses for violation of European GDPR regulations?",
                "manual_step7_q3_unanswerable.png",
            ),
        ]

        results = []
        assistant_msg_count = 0  # track how many assistant responses we've seen

        for q_label, q_text, screenshot_name in questions:
            print(f"\nAsking {q_label}: '{q_text}'")
            # Wait for textarea to be enabled before filling (previous stream may still be finishing)
            page.wait_for_selector("#chat-query-input:not([disabled])", timeout=30000)
            page.fill("#chat-query-input", q_text)
            page.click("#chat-send-btn")

            # Phase 1: Wait for a new non-empty assistant message to start appearing
            expected_count = assistant_msg_count + 1
            page.wait_for_function(
                f"""() => {{
                    const msgs = document.querySelectorAll('.whitespace-pre-wrap');
                    const assistantMsgs = Array.from(msgs).filter(el => el.textContent.trim().length > 10);
                    return assistantMsgs.length >= {expected_count};
                }}""",
                timeout=120000,
            )

            # Phase 2: Wait for streaming to finish — textarea re-enables when isStreaming=false
            page.wait_for_selector("#chat-query-input:not([disabled])", timeout=180000)
            assistant_msg_count = expected_count
            # Brief settle time for citations DOM
            time.sleep(0.5)

            page.screenshot(path=os.path.join(ARTIFACT_DIR, screenshot_name))
            print(f"Captured: {screenshot_name}")

            # Extract last assistant message text and citations
            messages = page.query_selector_all(".whitespace-pre-wrap")
            last_text = messages[-1].inner_text() if messages else "NO_RESPONSE"

            # Citations are in border-l elements inside assistant message divs
            citations = page.query_selector_all(".border-l.border-slate-300")
            citation_texts = [c.inner_text().replace("\n", " | ") for c in citations]

            results.append({
                "label": q_label,
                "question": q_text,
                "answer": last_text,
                "citations": citation_texts,
            })

            print(f"\n--- Output for {q_label} ---")
            # Use 'ignore' not 'replace' so readable ASCII content is preserved
            safe_text = last_text.encode('ascii', errors='ignore').decode('ascii')
            print(f"Answer:\n{safe_text}\n")
            if citation_texts:
                safe_citations = [c.encode('ascii', errors='ignore').decode('ascii') for c in citation_texts]
                print(f"Citations:\n" + "\n".join(safe_citations))

        browser.close()

    # Write full results to UTF-8 file (terminal may not support all chars)
    results_path = os.path.join(ARTIFACT_DIR, "e2e_rag_results.txt")
    with open(results_path, "w", encoding="utf-8") as f:
        for r in results:
            f.write(f"=== {r['label']} ===\n")
            f.write(f"Q: {r['question']}\n")
            f.write(f"A: {r['answer']}\n")
            if r['citations']:
                f.write("Citations:\n" + "\n".join(r['citations']) + "\n")
            f.write("\n")
    print(f"\nFull results saved to: {results_path}")

    print("\n=== Verification Completed Successfully ===")
    return results


if __name__ == "__main__":
    run_verification()
