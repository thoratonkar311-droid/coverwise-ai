"""Generates synthetic sample health insurance policy PDF for tests."""

from pathlib import Path
try:
    import pymupdf as fitz
except ImportError:
    import fitz  # type: ignore

PAGES = [
    """APEX HEALTH PLAN - SCHEDULE OF BENEFITS 2026
Plan Name: Apex Silver Advantage PPO
Policy ID: APX-2026-SLV-9012
Insurer: Apex Mutual Health Insurance Co.
Plan Year: 2026
Effective Date: 2026-01-01
Network: Apex Preferred National Network

SECTION 1: ANNUAL DEDUCTIBLES AND OUT-OF-POCKET MAXIMUMS
1.1 Annual Deductible:
- Individual (In-Network): $1,500.00
- Individual (Out-of-Network): $3,000.00
- Family (In-Network): $3,000.00
- Family (Out-of-Network): $6,000.00

1.2 Annual Out-of-Pocket Maximum:
- Individual (In-Network): $6,500.00
- Individual (Out-of-Network): $13,000.00
- Family (In-Network): $13,000.00
- Family (Out-of-Network): $26,000.00""",

    """APEX HEALTH PLAN - SCHEDULE OF BENEFITS 2026 (Page 2)
SECTION 2: COPAYMENTS AND COINSURANCE

2.1 Office Visits:
- Primary Care Physician (PCP): $25.00 copay per visit, deductible waived.
- Specialist Physician Visit: $50.00 copay per visit, deductible waived.
- Urgent Care Center: $75.00 copay per visit.
- Emergency Room (ER): $350.00 copay per visit (copay waived if admitted as inpatient).

2.2 Prescription Drug Benefits:
- Tier 1 (Generic Drugs): $10.00 copay (30-day supply).
- Tier 2 (Preferred Brand): $40.00 copay (30-day supply).
- Tier 3 (Non-Preferred Brand): $80.00 copay (30-day supply).
- Tier 4 (Specialty Drugs): 20% coinsurance up to a maximum of $250.00 per prescription.

2.3 General Coinsurance:
- In-Network Services: 20% coinsurance after deductible is met.
- Out-of-Network Services: 40% coinsurance after deductible is met.""",

    """APEX HEALTH PLAN - SCHEDULE OF BENEFITS 2026 (Page 3)
SECTION 3: INPATIENT AND OUTPATIENT SURGICAL SERVICES

3.1 Inpatient Hospital Stays:
- Semi-private room and board, surgery, nursing care: 20% coinsurance after in-network deductible.
- Prior authorization is strictly required at least 72 hours prior to all non-emergency elective admissions.

3.2 Outpatient Ambulatory Surgery:
- Ambulatory Surgical Center (ASC) facility fee: 20% coinsurance after in-network deductible.
- Surgeon and anesthesiologist professional fees: 20% coinsurance after in-network deductible.
- Elective outpatient surgery requires prior authorization from the Medical Review Board.

3.3 Diagnostic Imaging:
- Advanced Imaging (MRI, CT Scan, PET Scan): $150.00 copay plus 20% coinsurance after deductible.
- Standard X-Ray and Ultrasound: $40.00 copay, deductible waived.""",

    """APEX HEALTH PLAN - SCHEDULE OF BENEFITS 2026 (Page 4)
SECTION 4: GENERAL EXCLUSIONS AND LIMITATIONS

4.1 Excluded Services:
The following services and treatments are explicitly excluded from coverage under this policy:
- Cosmetic surgery or procedures performed primarily to improve physical appearance.
- Experimental, investigational, or unproven medical treatments.
- Adult routine dental examinations, cleanings, and restorative treatments.
- Routine adult refractive eye examinations, eyeglasses, and contact lenses.
- Weight loss surgeries (bariatric surgery) unless pre-authorized under severe medical necessity criteria.
- Alternative therapies including acupuncture, naturopathy, and chiropractic therapy exceeding 12 visits annually.

4.2 Appeals and Grievances:
Members have the right to file an internal grievance within 180 days of an adverse coverage determination."""
]


def generate_pdf(output_path: Path) -> Path:
    """Generate multi-page synthetic policy PDF."""
    doc = fitz.open()
    for text in PAGES:
        page = doc.new_page(width=595, height=842)
        rect = fitz.Rect(50, 50, 545, 792)
        page.insert_textbox(rect, text, fontsize=11, fontname="helv")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(output_path))
    doc.close()
    return output_path


if __name__ == "__main__":
    out = Path(__file__).parent / "sample_health_policy.pdf"
    generate_pdf(out)
    print(f"Generated {out} with {len(PAGES)} pages.")
