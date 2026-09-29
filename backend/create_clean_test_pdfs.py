import fitz

def create_policy_a():
    doc = fitz.open()
    page = doc.new_page(width=612, height=792) # Standard US Letter 612x792 pt
    
    text = """ALPHA HEALTH ASSURANCE LTD
POLICY SCHEDULE & CONTRACT CERTIFICATE

Policy Number: AH-GOLD-2026-991
Insurer: Alpha Health Assurance Ltd
Plan Name: Alpha Super Gold Shield
Policyholder Name: Vikram Sharma
Policy Period: 01-Jan-2026 to 31-Dec-2026
Sum Insured: INR 10,00,000 (Ten Lakhs Only)

SECTION 1: GENERAL TERMS AND WAITING PERIODS
1.1 Initial Waiting Period: 30 days from policy inception.
1.2 Specific Illness Waiting Period: 36 months waiting period applies to Total Knee Replacement and joint degenerative conditions.
1.3 Pre-Existing Diseases (PED) Waiting Period: 48 months.

SECTION 2: CO-PAYMENT AND DEDUCTIBLE
2.1 In-Network Hospitals: Co-payment is 0% for authorized network cashless hospitalization.
2.2 Non-Network Hospitals: 10% co-payment applies on all non-network claims.
2.3 Deductible: No compulsory deductible applies to this policy.

SECTION 3: BENEFIT SUB-LIMITS AND PROCEDURE RULES
3.1 Total Knee Replacement: Covered up to 60% of Sum Insured, subject to an absolute maximum limit of INR 600,000.
3.2 Cataract Surgery: Covered up to INR 50,000 per eye.
3.3 Room Rent Category: Single Private Room up to INR 10,000 per day. ICU capped at INR 20,000 per day.
"""
    # Use insert_textbox with generous rect
    rect = fitz.Rect(40, 40, 572, 750)
    page.insert_textbox(rect, text, fontsize=11, fontname="helv")
    doc.save("test_policies/Policy_A_Gold.pdf")
    doc.close()
    print("Created Policy_A_Gold.pdf successfully")

def create_policy_b():
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    
    text = """BETA CARE INSURANCE CORP
HEALTH INSURANCE POLICY CONTRACT

Policy Number: BC-SILVER-2026-442
Insurer: Beta Care Insurance Corp
Plan Name: Beta Health Advantage Silver
Policyholder Name: Priya Patel
Policy Period: 01-Feb-2026 to 31-Jan-2027
Sum Insured: INR 5,00,000 (Five Lakhs Only)

SECTION 1: GENERAL ELIGIBILITY & WAITING PERIODS
1.1 Initial Waiting Period: 30 days from commencement.
1.2 Specific Disease Waiting: 24 months waiting period applies to Total Knee Replacement.
1.3 Pre-Existing Conditions: 36 months waiting period.

SECTION 2: DEDUCTIBLE AND CO-PAYMENT
2.1 Compulsory Annual Deductible: An annual deductible of INR 10,000 applies to admissible claims before benefits are payable.
2.2 Mandatory Co-Payment: A 20% co-payment applies on all admissible hospitalization expenses across network facilities.
2.3 Non-Network Co-Payment: A 30% co-payment applies for non-network treatments.

SECTION 3: BENEFIT SUB-LIMITS AND PROCEDURE RULES
3.1 Joint Replacement Surgery: Total Knee Replacement is capped at 50% of Sum Insured (maximum INR 250,000).
3.2 Cataract Surgery: Covered up to INR 30,000 per eye.
3.3 Room Rent: Twin Sharing Room up to INR 5,000 per day.
"""
    rect = fitz.Rect(40, 40, 572, 750)
    page.insert_textbox(rect, text, fontsize=11, fontname="helv")
    doc.save("test_policies/Policy_B_Silver.pdf")
    doc.close()
    print("Created Policy_B_Silver.pdf successfully")

if __name__ == "__main__":
    create_policy_a()
    create_policy_b()
