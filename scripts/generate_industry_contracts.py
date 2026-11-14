"""
Generate two specialized, high-stakes demonstration contracts for LocalMind:
1. Demo_Hospital_Healthcare_EHR_Agreement.pdf (Hospital / Clinical Data Fiduciary Test)
2. Demo_Bank_Fintech_Cloud_Outsourcing_Agreement.pdf (Bank / Financial Fiduciary Test)

Both contain targeted DPDP Act 2023, RBI, and standard commercial compliance clauses.
"""
import pymupdf
import os

def generate_hospital_agreement(output_path: str = "Demo_Hospital_Healthcare_EHR_Agreement.pdf"):
    doc = pymupdf.open()

    # --- PAGE 1: Parties, Medical Recitals, Scope & Termination ---
    page1 = doc.new_page(width=595, height=842) # A4
    p1_text = """HOSPITAL ELECTRONIC HEALTH RECORDS & AI DIAGNOSTICS AGREEMENT

This Healthcare Data Processing & Cloud Diagnostics Agreement ("Agreement") is entered into as of November 15, 2026, by and between:
1. MediCloud AI Diagnostics Private Limited ("Data Processor" or "Vendor"), having its registered facility at Sector 62, Noida, Uttar Pradesh, India; and
2. Apex Multi-Speciality Hospitals & Research Institute ("Data Fiduciary" or "Hospital"), having its principal healthcare campus at Connaught Place, New Delhi, India.

RECITALS & APPLICABLE STATUTORY MANDATES
WHEREAS, Hospital operates multi-speciality tertiary care centers and maintains confidential Digital Personal Data including Electronic Health Records (EHR), patient clinical histories, diagnostic imaging (MRI/CT), pathology reports, and genomic data;
WHEREAS, Hospital is a designated Data Fiduciary governed by India's Digital Personal Data Protection Act (DPDP Act, 2023) and National Medical Commission (NMC) confidentiality mandates;
WHEREAS, Vendor provides AI-assisted diagnostic screening software and cloud medical record management.

SECTION 1: CLINICAL SERVICES & MEDICAL IMAGE PROCESSING
1.1 Tele-Radiology & EHR Processing. Vendor will host Hospital's radiology feeds and provide automated preliminary screening with 99.8% server availability.
1.2 Medical Emergency Support. Vendor's diagnostic assistance portal is available 24/7/365 for emergency trauma evaluations.

SECTION 2: TERM AND CLINICAL TERMINATION
2.1 Term. This Agreement shall remain in effect for three (3) years from the Effective Date.
2.2 Emergency Termination for Convenience. Hospital acknowledges that Vendor may terminate cloud hosting services without cause upon providing five (5) days prior written notice. Hospital agrees that upon such termination, patient diagnostic records may be permanently quarantined within forty-eight (48) hours.
2.3 Statutory Revocation. Hospital reserves the right to terminate immediately if Vendor suffers an unnotified patient data breach.
"""
    rect1 = pymupdf.Rect(50, 50, 545, 780)
    page1.insert_textbox(rect1, p1_text, fontsize=10, fontname="helv")
    page1.insert_text((50, 800), "Page 1 of 3 — Apex Hospitals & MediCloud Healthcare Agreement (CONFIDENTIAL)", fontsize=8, fontname="helv", color=(0.4, 0.4, 0.4))

    # --- PAGE 2: Patient Data Licensing, AI Training, DPDPA & Unlimited Exposure ---
    page2 = doc.new_page(width=595, height=842)
    p2_text = """SECTION 3: PATIENT HEALTH DATA PRIVACY & MACHINE LEARNING RIGHTS
3.1 Ownership of Hospital Data. Hospital retains legal title to raw patient clinical data under the DPDP Act 2023.
3.2 Patient Data License & Model Training (RESTRICTED CLAUSE). Hospital hereby grants Vendor an irrevocable, perpetual, worldwide, transferable license to de-identify, use, and process all patient Electronic Health Records, diagnostic scans, and clinical notes to train Vendor's internal commercial foundation AI models and commercial diagnostics algorithms.
3.3 Cross-Border Health Data Routing. Hospital consents that encrypted diagnostic telemetry may be routed and processed through secondary cloud clusters located outside India without prior Data Protection Board approval.

SECTION 4: INDEMNIFICATION & HOSPITAL STATUTORY LIABILITIES
4.1 Hospital Indemnification. Hospital agrees to defend, indemnify, and hold harmless Vendor from any regulatory penalties, patient lawsuits, or Data Protection Board of India inquiries resulting from inaccurate diagnostic outputs or alleged violations of DPDP Act consent requirements.
4.2 Vendor Disclaimer. Vendor provides its diagnostic AI on an "as-is" basis and disclaims all liability for clinical misdiagnoses or adverse patient medical outcomes.

SECTION 5: LIMITATION OF MEDICAL LIABILITY (CRITICAL EXPOSURE)
5.1 Unlimited Hospital Exposure. Hospital's liability under this Agreement for any alleged breach of data delivery or payment default shall be unlimited and without aggregate dollar ceiling.
5.2 Vendor Ceiling. Vendor's aggregate financial liability to Hospital for all claims including clinical downtime, system outages, or data leakage shall not exceed fifty thousand Indian Rupees (INR 50,000).
"""
    rect2 = pymupdf.Rect(50, 50, 545, 780)
    page2.insert_textbox(rect2, p2_text, fontsize=10, fontname="helv")
    page2.insert_text((50, 800), "Page 2 of 3 — Apex Hospitals & MediCloud Healthcare Agreement (CONFIDENTIAL)", fontsize=8, fontname="helv", color=(0.4, 0.4, 0.4))

    # --- PAGE 3: Breach Notification, Non-Compete & Jurisdiction ---
    page3 = doc.new_page(width=595, height=842)
    p3_text = """SECTION 6: SECURITY INCIDENT & STATUTORY BREACH REPORTING
6.1 Breach Notification. In the event of a confirmed cybersecurity compromise or unauthorized access to patient health data, Vendor shall notify Hospital within thirty (30) business days following forensic completion.
6.2 Hospital Statutory Duty. Hospital acknowledges that Section 8(6) of India's DPDP Act requires prompt notification to the Data Protection Board and affected Data Principals.

SECTION 7: MEDICAL STAFF RESTRICTIVE COVENANTS
7.1 Restrictive Clinical Covenant. For a period of twenty-four (24) months following termination, Hospital agrees that its attending radiologists, oncologists, and data administrators shall not consult with or advise any other competing digital health AI vendor in India.

SECTION 8: GOVERNING LAW & JURISDICTION
8.1 Governing Law. This Agreement shall be governed by and construed in accordance with the substantive laws of India, subject to DPDP Act 2023 rules.
8.2 Exclusive Jurisdiction. The parties agree that the competent courts situated in New Delhi, India shall have exclusive jurisdiction over all disputes arising hereunder.

IN WITNESS WHEREOF, the parties hereto have executed this Agreement by their authorized fiduciaries.

For Apex Multi-Speciality Hospitals:            For MediCloud AI Diagnostics:
Dr. R. K. Sharma, Medical Director               V. N. Nair, Chief Technology Officer
"""
    rect3 = pymupdf.Rect(50, 50, 545, 780)
    page3.insert_textbox(rect3, p3_text, fontsize=10, fontname="helv")
    page3.insert_text((50, 800), "Page 3 of 3 — Apex Hospitals & MediCloud Healthcare Agreement (CONFIDENTIAL)", fontsize=8, fontname="helv", color=(0.4, 0.4, 0.4))

    doc.save(output_path)
    print(f"Hospital Demo Contract saved to: {output_path}")


def generate_bank_agreement(output_path: str = "Demo_Bank_Fintech_Cloud_Outsourcing_Agreement.pdf"):
    doc = pymupdf.open()

    # --- PAGE 1: Parties, Banking Recitals, Scope & SLA ---
    page1 = doc.new_page(width=595, height=842)
    p1_text = """BANK CORE CLOUD OUTSOURCING & FINTECH SERVICES AGREEMENT

This Banking Infrastructure & Financial Services Master Agreement ("Agreement") is entered into as of November 15, 2026, by and between:
1. FinScale Cloud Technologies Private Limited ("Vendor" or "Service Provider"), having its registered corporate seat at Financial District, Gachibowli, Hyderabad, Telangana; and
2. Bharat Commercial Co-operative Bank Limited ("Bank" or "Regulated Entity"), a banking corporation licensed under the Banking Regulation Act, 1949, having its central office at Fort, Mumbai, Maharashtra, India.

RECITALS & REGULATORY FRAMEWORK
WHEREAS, Bank is a Scheduled Commercial Financial Institution and a designated Data Fiduciary processing highly sensitive customer financial data, Core Banking System (CBS) transaction feeds, and KYC records;
WHEREAS, Bank is strictly regulated by the Reserve Bank of India (RBI Master Direction on Outsourcing of Information Technology Services, 2023) and the Digital Personal Data Protection Act (DPDP Act, 2023);
WHEREAS, Service Provider offers multi-tenant core banking middleware, payment reconciliation pipelines, and customer risk scoring systems.

SECTION 1: BANKING CLOUD SERVICES & CBS INTEGRATION
1.1 Real-Time Reconciliation Middleware. Provider shall deliver 99.95% API uptime for automated UPI and RTGS ledger reconciliation.
1.2 RBI Audit Right. Provider acknowledges that RBI examiners and Bank internal auditors must be granted unimpeded inspection access to operational data centers upon five (5) days notice.

SECTION 2: TERM AND OUTSOURCING TERMINATION
2.1 Term. This Agreement shall endure for an initial duration of thirty-six (36) calendar months.
2.2 Termination for Convenience. Provider may terminate this banking middleware service without cause upon providing ten (10) days prior written notice to Bank. Upon such termination, Provider shall not be obligated to maintain live mirror databases beyond seventy-two (72) hours.
2.3 Regulatory Suspension. Bank may terminate without penalty if directed by the Reserve Bank of India or financial regulators.
"""
    rect1 = pymupdf.Rect(50, 50, 545, 780)
    page1.insert_textbox(rect1, p1_text, fontsize=10, fontname="helv")
    page1.insert_text((50, 800), "Page 1 of 3 — Bharat Commercial Bank & FinScale Outsourcing Agreement (CONFIDENTIAL)", fontsize=8, fontname="helv", color=(0.4, 0.4, 0.4))

    # --- PAGE 2: Financial Data Licensing, RBI Data Localization & Unlimited Liability ---
    page2 = doc.new_page(width=595, height=842)
    p2_text = """SECTION 3: FINANCIAL DATA OWNERSHIP & DATA RESIDENCY MANDATES
3.1 Exclusive Bank Ownership. All banking customer accounts, Aadhaar-linked verification records, account balances, and transactional logs remain the exclusive fiduciary property of Bank.
3.2 Proprietary Data License & Model Training. Bank hereby grants Provider a royalty-free, perpetual, transferable right to anonymize and ingest customer credit risk scores, payment patterns, and transaction metadata into Provider's proprietary commercial underwriting neural networks.
3.3 Data Localization & Cross-Border Restrictions. Provider covenants to store primary financial transaction data within India in compliance with RBI Directive on Storage of Payment System Data. Secondary analytics logs may be synchronized with foreign backup clusters.

SECTION 4: INDEMNIFICATION & REPOSITORY DEFENSE
4.1 Unilateral Bank Indemnity. Bank solely and unconditionally covenants to defend, indemnify, and hold harmless Provider from all customer claims, legal charges, regulatory penalties from RBI, or class actions arising out of ledger synchronization errors or system failure.
4.2 Provider Disclaimer. Provider disclaims all liability for banking business interruption, automated loan rejection disputes, or cyber fraud losses.

SECTION 5: LIMITATION OF FINANCIAL LIABILITY (CRITICAL EXPOSURE)
5.1 Unlimited Bank Liability. In no event shall Bank's aggregate financial liability under this Agreement be capped; Bank shall have unlimited liability for all direct and consequential damages.
5.2 Provider Cap. Provider's total aggregate liability under this Agreement for any and all claims shall be capped at one hundred thousand Indian Rupees (INR 1,00,000) or one month of maintenance fees.
"""
    rect2 = pymupdf.Rect(50, 50, 545, 780)
    page2.insert_textbox(rect2, p2_text, fontsize=10, fontname="helv")
    page2.insert_text((50, 800), "Page 2 of 3 — Bharat Commercial Bank & FinScale Outsourcing Agreement (CONFIDENTIAL)", fontsize=8, fontname="helv", color=(0.4, 0.4, 0.4))

    # --- PAGE 3: Cybersecurity Reporting, Non-Solicitation & Jurisdiction ---
    page3 = doc.new_page(width=595, height=842)
    p3_text = """SECTION 6: CYBERSECURITY INCIDENT NOTIFICATION & CERT-IN COMPLIANCE
6.1 Incident Notification Window. Provider agrees to report unauthorized intrusion attempts or customer data leaks to Bank within fourteen (14) business days of incident confirmation.
6.2 Statutory Compliance. Bank notes that CERT-In directions mandate cybersecurity incident reporting within six (6) hours, and DPDP Act requires immediate notification to the Data Protection Board.

SECTION 7: BANKING PERSONNEL RESTRICTIONS
7.1 Non-Compete & Key Staff Restriction. During the term and for eighteen (18) months thereafter, Bank agrees not to hire, engage, or contract with any engineering specialist or cloud architect employed by Provider.

SECTION 8: DISPUTE RESOLUTION & GOVERNING LAW
8.1 Governing Law. This Agreement shall be governed by, and interpreted in accordance with, the laws of the Republic of India and RBI regulations.
8.2 Arbitration & Jurisdiction. All disputes shall be finally resolved by binding arbitration in Mumbai under the Arbitration and Conciliation Act, 1996. The High Court of Bombay shall exercise supervisory jurisdiction.

IN WITNESS WHEREOF, the parties have signed this Agreement through their duly authorized signatories.

For Bharat Commercial Co-operative Bank:       For FinScale Cloud Technologies:
S. M. Joshi, Chief General Manager (IT)         K. S. Raman, Director of Strategic Accounts
"""
    rect3 = pymupdf.Rect(50, 50, 545, 780)
    page3.insert_textbox(rect3, p3_text, fontsize=10, fontname="helv")
    page3.insert_text((50, 800), "Page 3 of 3 — Bharat Commercial Bank & FinScale Outsourcing Agreement (CONFIDENTIAL)", fontsize=8, fontname="helv", color=(0.4, 0.4, 0.4))

    doc.save(output_path)
    print(f"Bank Demo Contract saved to: {output_path}")

if __name__ == "__main__":
    generate_hospital_agreement()
    generate_bank_agreement()

