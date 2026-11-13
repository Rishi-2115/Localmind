"""
Generate a realistic 3-page commercial SaaS & Master Services Agreement (MSA) PDF
specifically designed to test LocalMind's Clause Risk Analyzer & Citation Navigation.

Included Test Clauses:
- Page 1: Parties, Scope, Term & Asymmetric 7-Day Termination (HIGH RISK)
- Page 2: Unlimited Liability & Unilateral Indemnification (CRITICAL RISK)
- Page 3: Overbroad 3-Year Global Non-Compete & Foreign Governing Law (England & Wales) (HIGH/MEDIUM RISK)
"""
import pymupdf

def generate_demo_contract(output_path: str = "Demo_Master_Services_Agreement.pdf"):
    doc = pymupdf.open()

    # --- PAGE 1: Parties, Recitals, Termination ---
    page1 = doc.new_page(width=595, height=842) # A4 size
    p1_text = """MASTER SERVICES & CLOUD SOFTWARE AGREEMENT

This Master Services Agreement ("Agreement") is entered into as of November 15, 2026 ("Effective Date"), by and between:
1. Apex Cloud Solutions Private Limited ("Vendor" or "Provider"), having its principal place of business at Cyber City, Sector 24, Gurugram, India; and
2. Sterling Global Enterprises LLC ("Customer" or "Client"), having its registered office at Level 12, Tower B, Bandra Kurla Complex, Mumbai, India.

RECITALS
WHEREAS, Provider specializes in proprietary enterprise artificial intelligence and enterprise software hosting services;
WHEREAS, Customer desires to procure enterprise cloud services and consulting from Provider subject to the terms hereof.

SECTION 1: SCOPE OF SERVICES & DELIVERABLES
1.1 Cloud Infrastructure. Provider shall provide access to the enterprise deployment platform with 99.5% scheduled uptime.
1.2 Support & Service Level Agreement. Standard support shall be provided during business hours (9:00 AM to 6:00 PM IST).
1.3 Implementation & Data Migration. Customer shall furnish all reasonable cooperation and source data required for migration.

SECTION 2: TERM AND TERMINATION
2.1 Initial Term. This Agreement commences on the Effective Date and continues for a period of twenty-four (24) months.
2.2 Termination for Convenience. Customer acknowledges and agrees that Provider may terminate this Agreement without cause at any time upon providing seven (7) days prior written notice to Customer. Upon such termination, all outstanding unpaid invoices shall become immediately due and payable, and Provider shall have no obligation to preserve Customer data beyond forty-eight (48) hours.
2.3 Termination for Material Breach. Either party may terminate immediately if the other party enters into insolvency, liquidation, or commits an incurable material breach.
"""
    # Insert formatted text with margins
    rect1 = pymupdf.Rect(50, 50, 545, 780)
    page1.insert_textbox(rect1, p1_text, fontsize=10, fontname="helv")
    page1.insert_text((50, 800), "Page 1 of 3 — Confidential & Proprietary Master Agreement", fontsize=8, fontname="helv", color=(0.4, 0.4, 0.4))

    # --- PAGE 2: Liability, Indemnification, Intellectual Property ---
    page2 = doc.new_page(width=595, height=842)
    p2_text = """SECTION 3: INTELLECTUAL PROPERTY & DATA PRIVACY
3.1 Proprietary Ownership. Provider retains all right, title, and interest in and to all AI models, software algorithms, methodologies, and system architectures developed or utilized in connection with the Services.
3.2 Customer Data License. Customer hereby grants Provider an irrevocable, perpetual, worldwide, royalty-free license to use, reproduce, modify, and train internal machine learning models on Customer Data and confidential business communications submitted to the platform.
3.3 Data Protection. Provider agrees to implement industry-standard security measures compliant with the Digital Personal Data Protection Act (DPDPA), 2023.

SECTION 4: INDEMNIFICATION (UNILATERAL OBLIGATION)
4.1 Customer Indemnity. Customer solely and unconditionally agrees to defend, indemnify, and hold harmless Provider, its affiliates, directors, employees, and licensors from and against any and all claims, liabilities, judgments, damages, fines, legal fees, and operational costs arising out of:
    (a) Any breach of this Agreement by Customer or its authorized personnel;
    (b) Any third-party regulatory investigation, intellectual property claim, or privacy dispute relating to Customer Data;
    (c) Any interruption of Customer's business operations resulting from reliance on generative artificial intelligence outputs.
4.2 Provider Disclaimer. Provider provides NO indemnification, defense, or financial reimbursement to Customer for any third-party intellectual property infringement claims arising from Provider's software or AI models.

SECTION 5: LIMITATION OF LIABILITY (UNLIMITED EXPOSURE)
5.1 Unlimited Customer Liability. In no event shall Customer's aggregate liability under this Agreement be subject to any financial cap or dollar ceiling. Customer shall have unlimited liability for all direct, indirect, special, punitive, incidental, and consequential damages, including loss of profits, loss of data, and business interruption.
5.2 Provider Liability Limitation. Provider's total aggregate liability arising out of or related to this Agreement under any legal theory (contract, tort, negligence, or strict liability) shall strictly be limited to fifty US Dollars ($50.00 USD).
"""
    rect2 = pymupdf.Rect(50, 50, 545, 780)
    page2.insert_textbox(rect2, p2_text, fontsize=10, fontname="helv")
    page2.insert_text((50, 800), "Page 2 of 3 — Confidential & Proprietary Master Agreement", fontsize=8, fontname="helv", color=(0.4, 0.4, 0.4))

    # --- PAGE 3: Non-Compete, Governing Law, Execution ---
    page3 = doc.new_page(width=595, height=842)
    p3_text = """SECTION 6: RESTRICTIVE COVENANTS & NON-COMPETITION
6.1 Restrictive Non-Compete Covenant. During the term of this Agreement and for a period of thirty-six (36) months following expiration or termination for any reason, Customer covenants and agrees that it shall not, directly or indirectly, develop, market, invest in, or solicit customers for any competitive artificial intelligence, natural language copilot, or legal technology software product within the global market.
6.2 Non-Solicitation of Personnel. Neither party shall solicit or recruit any developer or engineer of the other party without prior written authorization.

SECTION 7: GOVERNING LAW AND DISPUTE RESOLUTION
7.1 Governing Law. This Agreement shall be governed by, construed, and enforced in accordance with the substantive laws of England and Wales, without regard to conflict of law principles.
7.2 Exclusive Jurisdiction. The courts of London, England shall have exclusive jurisdiction over any claim, controversy, or litigation arising out of or in connection with this Agreement. The parties explicitly waive any objection to venue in London, England.
7.3 Waiver of Jury Trial. Each party irrevocably waives all rights to a trial by jury in any legal proceeding arising out of this contract.

IN WITNESS WHEREOF, the duly authorized representatives of the parties have executed this Master Services Agreement as of the date first above written.

FOR APEX CLOUD SOLUTIONS PVT LTD:
Signature: __________________________
Name: Rajeshwar Sen
Title: Chief Executive Officer

FOR STERLING GLOBAL ENTERPRISES LLC:
Signature: __________________________
Name: Vikramaditya Malhotra
Title: Managing Director & General Counsel
"""
    rect3 = pymupdf.Rect(50, 50, 545, 780)
    page3.insert_textbox(rect3, p3_text, fontsize=10, fontname="helv")
    page3.insert_text((50, 800), "Page 3 of 3 — Confidential & Proprietary Master Agreement", fontsize=8, fontname="helv", color=(0.4, 0.4, 0.4))

    doc.save(output_path)
    doc.close()
    print(f"Generated demo contract at: {output_path}")

if __name__ == "__main__":
    generate_demo_contract("Demo_Master_Services_Agreement.pdf")
