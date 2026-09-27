"""Generates three diverse synthetic insurance policy PDFs for quality assurance:
1. Indian Health Insurance Policy (INR-focused, Star Comprehensive Health Insurance)
2. HDHP Health Policy (USD-focused, BlueShield Horizon HDHP HSA-Qualified)
3. Global Executive Health Policy (EUR-focused, EuroHealth Global Executive Care)
"""

from pathlib import Path
try:
    import pymupdf as fitz
except ImportError:
    import fitz  # type: ignore

# -----------------------------------------------------------------------------
# 1. INDIAN HEALTH POLICY (INR-focused)
# -----------------------------------------------------------------------------
INDIAN_PAGES = [
    """STAR COMPREHENSIVE HEALTH INSURANCE - SCHEDULE OF BENEFITS 2026
Plan Name: Star Comprehensive Gold Plan
Policy ID: SHI-2026-IND-7788
Insurer: Star Health & Allied Insurance Co.
Plan Year: 2026
Effective Date: 2026-04-01
Currency: INR
Network: Star National Cashless Hospital Network

SECTION 1: ANNUAL DEDUCTIBLES AND OUT-OF-POCKET LIMITS
1.1 Annual Deductible:
- Individual (In-Network): INR 25,000.00
- Individual (Out-of-Network): INR 50,000.00
- Family (In-Network): INR 50,000.00
- Family (Out-of-Network): INR 100,000.00

1.2 Annual Out-of-Pocket Maximum:
- Individual (In-Network): INR 200,000.00
- Individual (Out-of-Network): INR 400,000.00
- Family (In-Network): INR 400,000.00
- Family (Out-of-Network): INR 800,000.00""",

    """STAR COMPREHENSIVE HEALTH INSURANCE - SCHEDULE OF BENEFITS 2026 (Page 2)
SECTION 2: COPAYMENTS AND COINSURANCE

2.1 Outpatient Consultations (OPD):
- Primary Care Physician (PCP): INR 500.00 copay per consultation.
- Specialist Physician Visit: INR 1,000.00 copay per consultation.
- Urgent Care Center: INR 1,500.00 copay per visit.
- Emergency Room (ER): INR 2,500.00 copay per emergency admission.
Note: Cashless OPD consultations have deductible waived at empaneled clinics.

2.2 Coinsurance Obligations:
- In-Network Services: 10% coinsurance after deductible is satisfied.
- Out-of-Network Services: 25% coinsurance after deductible is satisfied.""",

    """STAR COMPREHENSIVE HEALTH INSURANCE - SCHEDULE OF BENEFITS 2026 (Page 3)
SECTION 3: INPATIENT HOSPITALIZATION AND PRE-AUTHORIZATION

3.1 Inpatient Hospital Stays:
- Semi-private room and board, nursing care, ICU charges: 10% coinsurance after in-network deductible.
- Cashless hospitalization requires prior authorization at least 48 hours prior to planned elective admission.
- Emergency hospitalization notifications must be submitted within 24 hours of admission.

3.2 Outpatient Daycare Procedures:
- Cataract, dialysis, and chemotherapy daycare treatments: 10% coinsurance.
- Outpatient surgical procedures require prior authorization from the Third Party Administrator (TPA).

3.3 Waiting Periods:
- An initial waiting period of 30 days applies from policy inception for all illnesses except accidental trauma.
- A waiting period of 24 months applies for all specified pre-existing diseases.""",

    """STAR COMPREHENSIVE HEALTH INSURANCE - SCHEDULE OF BENEFITS 2026 (Page 4)
SECTION 4: GENERAL EXCLUSIONS AND SPECIFIC LIMITS

4.1 Excluded Services:
The following medical procedures and expenses are strictly excluded from coverage:
- Cosmetic surgery or procedures performed primarily to improve physical appearance.
- Experimental, investigational, or unproven medical treatments.
- Adult routine dental cleanings, cosmetic dentistry, and dental implants.
- Routine adult eye refraction, spectacles, and contact lenses.
- Adventure sports injuries sustained during professional motor racing or mountaineering.

4.2 Sub-limits:
- AYUSH alternative treatments covered up to INR 50,000.00 per policy year.
- Alternative therapies and physiotherapy exceeding 12 visits annually are excluded.

SECTION 5: GENERAL TERMS AND OVERRIDING CLAUSES
5.1 Notwithstanding any conflicting statements in Section 2, all outpatient claims are subject to annual policy deductible.""",
]

# -----------------------------------------------------------------------------
# 2. HDHP HEALTH POLICY (USD-focused)
# -----------------------------------------------------------------------------
HDHP_PAGES = [
    """BLUESHIELD HORIZON HDHP - SCHEDULE OF BENEFITS 2026
Plan Name: BlueShield Horizon HDHP HSA-Qualified Plan
Policy ID: BSH-2026-HDHP-4451
Insurer: BlueShield Horizon Insurance Group
Plan Year: 2026
Effective Date: 2026-01-01
Currency: USD
Network: BlueShield Preferred Regional Network

SECTION 1: ANNUAL DEDUCTIBLES AND OUT-OF-POCKET MAXIMUMS
1.1 Annual Deductible:
- Individual (In-Network): $3,200.00
- Individual (Out-of-Network): $6,400.00
- Family (In-Network): $6,400.00
- Family (Out-of-Network): $12,800.00

1.2 Annual Out-of-Pocket Maximum:
- Individual (In-Network): $7,500.00
- Individual (Out-of-Network): $15,000.00
- Family (In-Network): $15,000.00
- Family (Out-of-Network): $30,000.00

1.3 Preventive Wellness Benefit:
- Preventive wellness examinations and screening mammograms: 100% covered with no cost sharing.""",

    """BLUESHIELD HORIZON HDHP - SCHEDULE OF BENEFITS 2026 (Page 2)
SECTION 2: COPAYMENTS AND COINSURANCE

2.1 Medical Office Visits:
- Primary Care Physician (PCP): $30.00 copay per visit after deductible.
- Specialist Physician Visit: $60.00 copay per visit after deductible.
- Urgent Care Center: $80.00 copay per visit.
- Emergency Room (ER): $400.00 copay per visit.

2.2 Prescription Benefits:
- Tier 1 (Generic Drugs): $15.00 copay.
- Tier 4 (Specialty Drugs): 20% coinsurance up to a maximum of $300.00 per prescription.

2.3 General Coinsurance:
- In-Network Services: 15% coinsurance after deductible is met.
- Out-of-Network Services: 35% coinsurance after deductible is met.""",

    """BLUESHIELD HORIZON HDHP - SCHEDULE OF BENEFITS 2026 (Page 3)
SECTION 3: INPATIENT SURGERY AND PRIOR AUTHORIZATION

3.1 Inpatient Admissions:
- Hospital room, board, and inpatient surgical procedures: 15% coinsurance after deductible.
- Prior authorization is strictly required at least 48 hours prior to all non-emergency elective admissions.

3.2 Outpatient Surgical Interventions:
- Outpatient ambulatory surgery requires prior authorization from the Medical Review Board.

3.3 Waiting Periods:
- A waiting period of 6 months applies for major restorative dental procedures.
- A waiting period of 12 months applies for orthodontic treatments.

3.4 Diagnostic Laboratory Clarification:
- Except as provided in Section 1.3, out-of-network preventive diagnostic labs subject to 35% coinsurance and calendar deductible.""",

    """BLUESHIELD HORIZON HDHP - SCHEDULE OF BENEFITS 2026 (Page 4)
SECTION 4: GENERAL EXCLUSIONS AND BENEFIT LIMITS

4.1 Excluded Services:
The following treatments are explicitly non-covered under this policy:
- Cosmetic surgery or procedures performed primarily to improve physical appearance.
- Laser eye refractive surgery (LASIK or PRK).
- Adult routine dental examinations, cleanings, and restorative treatments.
- Experimental, investigational, or unproven medical treatments.
- Weight loss surgeries (bariatric procedures) without documented chronic co-morbidities.

4.2 Visit Limitations:
- Chiropractic therapy and alternative therapies exceeding 20 visits annually are excluded."""
]

# -----------------------------------------------------------------------------
# 3. GLOBAL EXECUTIVE HEALTH POLICY (EUR-focused)
# -----------------------------------------------------------------------------
GLOBAL_PAGES = [
    """EUROHEALTH GLOBAL EXECUTIVE CARE - BENEFIT SCHEDULE 2026
Plan Name: EuroHealth Global Executive Care Plan
Policy ID: EHG-2026-GLB-1088
Insurer: EuroHealth International Life & Medical
Plan Year: 2026
Effective Date: 2026-01-01
Currency: EUR
Network: EuroHealth Global Premier Network

SECTION 1: ANNUAL DEDUCTIBLES AND OUT-OF-POCKET LIMITS
1.1 Annual Deductible:
- Individual (In-Network): €1,000.00
- Individual (Out-of-Network): €2,500.00
- Family (In-Network): €2,000.00
- Family (Out-of-Network): €5,000.00

1.2 Annual Out-of-Pocket Maximum:
- Individual (In-Network): €5,000.00
- Individual (Out-of-Network): €10,000.00
- Family (In-Network): €10,000.00
- Family (Out-of-Network): €20,000.00""",

    """EUROHEALTH GLOBAL EXECUTIVE CARE - BENEFIT SCHEDULE 2026 (Page 2)
SECTION 2: COPAYMENTS AND COINSURANCE

2.1 Consultations and Ambulatory Care:
- Primary Care Physician (PCP): €20.00 copay per visit.
- Specialist Physician Visit: €45.00 copay per consultation.
- Urgent Care Center: €60.00 copay per episode.
- Emergency Room (ER): €150.00 copay per emergency visit.
- Emergency medical transport covered at 100% worldwide without prior authorization.

2.2 General Coinsurance:
- In-Network Services: 10% coinsurance after deductible is met.
- Out-of-Network Services: 30% coinsurance after deductible is met.""",

    """EUROHEALTH GLOBAL EXECUTIVE CARE - BENEFIT SCHEDULE 2026 (Page 3)
SECTION 3: INPATIENT TREATMENT AND PRIOR AUTHORIZATION

3.1 Inpatient Care:
- Private hospital suite, surgery, anesthesiology: 10% coinsurance after in-network deductible.
- Prior authorization is strictly required at least 96 hours prior to all non-emergency elective admissions.

3.2 Outpatient Surgical Interventions:
- Outpatient surgical procedures require prior authorization from the Medical Advisory Council.

3.3 Waiting Periods:
- A waiting period of 10 months applies for maternity and childbirth coverage.
- A waiting period of 12 months applies for major organ transplant procedures.""",

    """EUROHEALTH GLOBAL EXECUTIVE CARE - BENEFIT SCHEDULE 2026 (Page 4)
SECTION 4: GENERAL EXCLUSIONS AND RESTRICTIONS

4.1 Excluded Services:
The following services and supplies are strictly excluded from coverage:
- Cosmetic surgery or procedures performed primarily to improve physical appearance.
- Experimental, investigational, or unproven medical treatments.
- Adult routine dental examinations, cleanings, and tooth whitening.
- Off-label drug administration without approved clinical trial protocol.
- Elective wellness retreat therapies and spa treatments.

4.2 Visit and Value Limits:
- Tier 4 specialty drugs capped at a maximum of €500.00 per prescription.
- Psychiatric and mental health outpatient care exceeding 15 visits annually is excluded.

SECTION 5: OVERRIDING TRANSPORT REGULATIONS
5.1 Notwithstanding Section 2.1, all medical transport strictly subject to advance insurer authorization."""
]


def generate_pdf(pages: list[str], output_path: Path) -> Path:
    """Render pages into a standardized multi-page PDF document."""
    doc = fitz.open()
    for text in pages:
        page = doc.new_page(width=595, height=842)
        rect = fitz.Rect(50, 50, 545, 792)
        page.insert_textbox(rect, text, fontsize=11, fontname="helv")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(output_path))
    doc.close()
    return output_path


def main():
    base_dir = Path(__file__).resolve().parent
    
    ind_pdf = base_dir / "indian_health_policy.pdf"
    generate_pdf(INDIAN_PAGES, ind_pdf)
    print(f"Generated {ind_pdf.name} ({len(INDIAN_PAGES)} pages)")

    hdhp_pdf = base_dir / "hdhp_health_policy.pdf"
    generate_pdf(HDHP_PAGES, hdhp_pdf)
    print(f"Generated {hdhp_pdf.name} ({len(HDHP_PAGES)} pages)")

    glb_pdf = base_dir / "global_exec_policy.pdf"
    generate_pdf(GLOBAL_PAGES, glb_pdf)
    print(f"Generated {glb_pdf.name} ({len(GLOBAL_PAGES)} pages)")


if __name__ == "__main__":
    main()
