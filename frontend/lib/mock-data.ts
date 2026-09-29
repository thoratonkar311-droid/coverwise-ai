import {
  PolicySummary,
  Policy,
  AnalysisResult,
  EvidenceReference,
  RecentAnalysisRecord,
  SimulationRequest,
  SimulationResult,
  DashboardOverview,
  Treatment,
} from "@/types";

export const DEMO_POLICY: PolicySummary = {
  id: "pol-care-premier-01",
  planName: "Care Premier Health Assurance Plan",
  insurerName: "Care Health Insurance Co. Ltd.",
  policyNumber: "CH-2026-9812401",
  policyPeriod: "01 Apr 2026 – 31 Mar 2027",
  sumInsured: 1000000,
  deductible: 15000,
  copayPercent: 10,
  roomRentLimit: "Single Private Room (Up to ₹5,000/day)",
  roomRentCondition: "Proportionate deduction on total medical expenses if higher room tier chosen",
  networkType: "Preferred Cashless In-Network (Tier 1)",
  waitingPeriodMonths: 24,
  categories: [
    { name: "Inpatient Hospitalization", status: "Covered", sublimit: "Up to Sum Insured" },
    { name: "Daycare Treatments (540+ Procedures)", status: "Covered", sublimit: "Full Allowance" },
    { name: "Joint Replacement & Orthopedic", status: "Covered with 10% Co-pay", sublimit: "₹2,50,000" },
    { name: "Diagnostic Advanced Scans (MRI/CT)", status: "Covered", sublimit: "Contracted Tariff" },
    { name: "Cosmetic / Weight Loss Surgeries", status: "Excluded", sublimit: "Non-Covered" },
    { name: "Ayush Alternative Treatment", status: "Partial", sublimit: "Up to ₹50,000" },
  ],
};

export const DEMO_FULL_POLICY: Policy = {
  ...DEMO_POLICY,
  uploadedAt: "2026-09-26T10:30:00Z",
  documentFileName: "Care_Premier_Policy_Schedule_2026.pdf",
  documentFileSizeBytes: 2450000,
  ocrConfidence: 98.4,
  rules: [
    {
      id: "rule-01",
      category: "Room Rent",
      ruleName: "Single Private Room Ceiling",
      description: "Admissible room category capped at ₹5,000/day with proportionate deduction on associated medical fees for higher room categories.",
      admissibilityStatus: "Covered",
      sublimit: "₹5,000/day",
      clauseCitation: "Section 2.4",
    },
    {
      id: "rule-02",
      category: "Co-payment",
      ruleName: "Joint Replacement Mandatory Co-pay",
      description: "10% mandatory co-payment on all orthopedic joint replacement surgeries.",
      admissibilityStatus: "Partial",
      copayPercent: 10,
      clauseCitation: "Section 4.1.2",
    },
    {
      id: "rule-03",
      category: "Waiting Period",
      ruleName: "Pre-existing Disease Waiting Period",
      description: "24 months continuous coverage required prior to claiming expenses for named pre-existing conditions.",
      admissibilityStatus: "Covered",
      waitingPeriodMonths: 24,
      clauseCitation: "Section 1.3",
    },
    {
      id: "rule-04",
      category: "Exclusions",
      ruleName: "General Non-Admissible Consumables",
      description: "Gloves, PPE kits, sanitizers, surgical gowns, and administrative admission processing fees are non-payable.",
      admissibilityStatus: "Excluded",
      clauseCitation: "Annexure I: List of Non-Admissible Items",
    },
  ],
};

export const DEMO_TREATMENTS: Treatment[] = [
  {
    id: "trt-knee",
    name: "Total Knee Replacement (Unilateral)",
    category: "Inpatient Orthopedic Surgery",
    cptCode: "CPT 27447",
    typicalCostRange: { min: 220000, max: 310000, currency: "INR" },
  },
  {
    id: "trt-cataract",
    name: "Cataract Surgery with Monofocal IOL",
    category: "Daycare Ophthalmology",
    cptCode: "CPT 66984",
    typicalCostRange: { min: 35000, max: 60000, currency: "INR" },
  },
  {
    id: "trt-mri",
    name: "MRI Diagnostic Brain Scan (with Contrast)",
    category: "Advanced Diagnostic Radiology",
    cptCode: "CPT 70553",
    typicalCostRange: { min: 18000, max: 28000, currency: "INR" },
  },
  {
    id: "trt-bariatric",
    name: "Bariatric Gastric Bypass Surgery",
    category: "Metabolic / Weight Management Surgery",
    cptCode: "CPT 43644",
    typicalCostRange: { min: 280000, max: 380000, currency: "INR" },
  },
];

export const DEMO_EVIDENCE_KNEE: EvidenceReference[] = [
  {
    id: "ev-01",
    title: "Major Orthopedic Joint Replacement Rule",
    sourceDoc: "Care_Premier_Policy_Schedule_2026.pdf",
    pageNumber: "Page 18, Table 4.1",
    clauseReference: "Section 4.1.2: Surgical Sub-limits & Co-payments",
    sourceText:
      "For Major Joint Replacement Surgeries (including Unilateral or Bilateral Total Knee Replacement), the Company's liability is capped at the contracted tariff rate subject to an applicable 10% mandatory co-payment on admissible expenses.",
    aiInterpretation:
      "Identified procedure category 'Total Knee Replacement'. Semantic analysis extracts mandatory 10% co-payment rule and standard implant allowance ceiling.",
    deterministicRule:
      "Formula: Admissible = MIN(Billed, Contracted Rate ₹2,35,000) - Deductible (₹15,000). Insurer Share = 90% of (Admissible) = ₹1,98,000. Patient Share = Deductible (₹15,000) + 10% Co-pay (₹22,000) + Consumables (₹1,500) = ₹38,500.",
    calculationImpact: "Increases patient liability by ₹22,000 via mandatory 10% co-pay rule.",
    confidence: 97.4,
    category: "Co-payment & Tariff Limit",
  },
  {
    id: "ev-02",
    title: "Room Category Capping & Proportionate Deductions",
    sourceDoc: "Care_Premier_Policy_Schedule_2026.pdf",
    pageNumber: "Page 12, Clause 2.4",
    clauseReference: "Section 2.4: Room Category Admissibility",
    sourceText:
      "Admissible room category is Single Private A/C Room up to ₹5,000 per 24 hours. If an insured opts for a room with rent exceeding this ceiling, all associated medical, surgical, and nursing expenses shall be reduced proportionately.",
    aiInterpretation:
      "Selected room category 'Single Private Room' satisfies the ₹5,000/day threshold. Proportionate penalty clause is NOT triggered.",
    deterministicRule:
      "Condition Check: Room Rent (₹4,800/day) <= Limit (₹5,000/day). Result: Proportionate penalty multiplier = 1.0 (No penalty applied).",
    calculationImpact: "Zero penalty applied. Standard 100% room rate admissibility preserved.",
    confidence: 99.1,
    category: "Room Rent Condition",
  },
  {
    id: "ev-03",
    title: "Consumable & Non-Payable Medical Items Schedule",
    sourceDoc: "Care_Premier_Policy_Schedule_2026.pdf",
    pageNumber: "Annexure I: List of Non-Admissible Items",
    clauseReference: "Schedule 3: Disallowed Items and Non-Medical Sundries",
    sourceText:
      "Expenses incurred towards gloves, PPE kits, admission charges, sanitizers, surgical gowns, and biomedical waste disposal are non-payable by the insurer and remain the patient's direct responsibility.",
    aiInterpretation:
      "Hospital billing estimate includes standard ₹8,000 in surgical sundries and administrative items classified as non-payable under Annexure I.",
    deterministicRule:
      "Deduction: Non-admissible consumables ₹8,000 separated entirely from insurer liability calculation.",
    calculationImpact: "Direct ₹8,000 out-of-pocket addition to patient responsibility.",
    confidence: 94.6,
    category: "Non-Payable Exclusion",
  },
];

export const DEMO_COVERAGE_SCENARIOS: Record<string, AnalysisResult> = {
  knee: {
    id: "analysis-knee-01",
    policyId: "pol-care-premier-01",
    treatmentName: "Total Knee Replacement (Unilateral)",
    treatmentCategory: "Inpatient Orthopedic Surgery",
    cptCode: "CPT 27447",
    coverageStatus: "Partially Covered",
    coveragePercentage: 85.2,
    estimatedTotalCost: 260000,
    estimatedInsuranceShare: 221500,
    estimatedPatientShare: 38500,
    deductibleApplicable: 15000,
    copayAmount: 22000,
    sublimitApplied: 250000,
    nonPayableConsumables: 8000,
    waitingPeriodStatus: "Satisfied (Policy active 28 months vs 24 month requirement)",
    roomRuleApplied: "Single Private Room (Admissible within ₹5,000/day cap)",
    exclusionsList: [
      "Non-payable hospital consumables & PPE kit sundries (₹8,000 estimate)",
      "High-end motorized post-operative mobility walker",
      "Non-medical administrative admission processing fee",
    ],
    evidenceList: DEMO_EVIDENCE_KNEE,
    evaluatedAt: "2026-09-26T14:20:00Z",
  },
  cataract: {
    id: "analysis-cataract-01",
    policyId: "pol-care-premier-01",
    treatmentName: "Cataract Surgery with Monofocal IOL",
    treatmentCategory: "Daycare Ophthalmology",
    cptCode: "CPT 66984",
    coverageStatus: "Likely Covered",
    coveragePercentage: 92.5,
    estimatedTotalCost: 45000,
    estimatedInsuranceShare: 41625,
    estimatedPatientShare: 3375,
    deductibleApplicable: 0,
    copayAmount: 0,
    sublimitApplied: 50000,
    nonPayableConsumables: 3375,
    waitingPeriodStatus: "Satisfied (12-month cataract waiting period completed)",
    roomRuleApplied: "Daycare Procedure (Room rent cap not applicable)",
    exclusionsList: [
      "Premium Toric/Multifocal lens upgrade delta (Patient personal choice)",
      "Protective postoperative sunglasses kit",
    ],
    evidenceList: [
      {
        id: "ev-cat-01",
        title: "Daycare Cataract Surgery Allowance",
        sourceDoc: "Care_Premier_Policy_Schedule_2026.pdf",
        pageNumber: "Page 22, Section 5.3",
        clauseReference: "Section 5.3: Ophthalmology & Daycare Lens Limits",
        sourceText:
          "Cataract procedures are covered up to ₹50,000 per eye inclusive of monofocal intraocular lens. Daycare hospitalization without 24-hr stay is fully admissible.",
        aiInterpretation:
          "Target procedure cost (₹45,000) falls completely within the ₹50,000 per-eye limit. Full daycare admissibility confirmed.",
        deterministicRule:
          "Admissible: ₹45,000 - Non-medical sundries (₹3,375) = ₹41,625 covered by insurer at 100%.",
        calculationImpact: "Insurer covers ₹41,625. Patient responsibility limited to consumables ₹3,375.",
        confidence: 98.2,
        category: "Daycare Allowance",
      },
    ],
    evaluatedAt: "2026-09-22T09:15:00Z",
  },
  mri: {
    id: "analysis-mri-01",
    policyId: "pol-care-premier-01",
    treatmentName: "MRI Diagnostic Brain Scan (with Contrast)",
    treatmentCategory: "Advanced Diagnostic Radiology",
    cptCode: "CPT 70553",
    coverageStatus: "Likely Covered",
    coveragePercentage: 86.4,
    estimatedTotalCost: 22000,
    estimatedInsuranceShare: 19000,
    estimatedPatientShare: 3000,
    deductibleApplicable: 0,
    copayAmount: 0,
    sublimitApplied: 25000,
    nonPayableConsumables: 3000,
    waitingPeriodStatus: "No waiting period applicable for diagnostic radiology",
    roomRuleApplied: "Outpatient / Diagnostic center (No room requirement)",
    exclusionsList: [
      "Specialty contrast allergy pre-screen panel (Non-covered ancillary)",
      "Unregistered film duplication fee",
    ],
    evidenceList: [
      {
        id: "ev-mri-01",
        title: "Advanced Outpatient Diagnostic Investigations",
        sourceDoc: "Care_Premier_Policy_Schedule_2026.pdf",
        pageNumber: "Page 16, Section 3.7",
        clauseReference: "Section 3.7: Diagnostic Imaging Coverage",
        sourceText:
          "Diagnostic MRI and CT scans prescribed by a specialist are payable up to contracted tariff rates at authorized diagnostic network centers.",
        aiInterpretation:
          "Referred MRI scan verified as admissible in-network investigation. Standard diagnostic rider active.",
        deterministicRule:
          "Formula: Contracted rate allowance ₹19,000 paid by insurer; contrast fee difference ₹3,000 patient responsibility.",
        calculationImpact: "Insurer liability: ₹19,000. Patient liability: ₹3,000.",
        confidence: 96.5,
        category: "Diagnostic Rider",
      },
    ],
    evaluatedAt: "2026-09-18T16:45:00Z",
  },
  bariatric: {
    id: "analysis-bariatric-01",
    policyId: "pol-care-premier-01",
    treatmentName: "Bariatric Gastric Bypass Surgery",
    treatmentCategory: "Metabolic / Weight Management Surgery",
    cptCode: "CPT 43644",
    coverageStatus: "Not Covered",
    coveragePercentage: 0,
    estimatedTotalCost: 320000,
    estimatedInsuranceShare: 0,
    estimatedPatientShare: 320000,
    deductibleApplicable: 0,
    copayAmount: 0,
    sublimitApplied: 0,
    nonPayableConsumables: 0,
    waitingPeriodStatus: "Exclusion active (Policy does not include Bariatric Endorsement)",
    roomRuleApplied: "Not Applicable (Procedure Excluded)",
    exclusionsList: [
      "General Exclusion Code EX-14: Surgical treatment of obesity and weight control",
      "Absence of secondary life-threatening BMI >45 documented comorbidity endorsement",
    ],
    evidenceList: [
      {
        id: "ev-bar-01",
        title: "Specific Policy Exclusion: Obesity & Weight Control",
        sourceDoc: "Care_Premier_Policy_Schedule_2026.pdf",
        pageNumber: "Page 34, Exclusion 14",
        clauseReference: "General Exclusions §EX-14",
        sourceText:
          "The Company shall not be liable to make any payment under this Policy in respect of any expenses for surgery or treatment related to weight reduction, morbid obesity, or cosmetic contouring.",
        aiInterpretation:
          "Explicit negative clause detected for Bariatric surgical classification. No qualifying endocrinologist endorsement found in active schedule.",
        deterministicRule:
          "Rule EX-14: Admissibility = 0%. Insurer share = ₹0. Total estimated treatment remains 100% patient responsibility.",
        calculationImpact: "Total claim disallowance. Patient responsibility is 100% (₹3,20,000).",
        confidence: 99.5,
        category: "Explicit Exclusion",
      },
    ],
    evaluatedAt: "2026-09-14T11:00:00Z",
  },
};

export const DEMO_RECENT_ANALYSES: RecentAnalysisRecord[] = [
  {
    id: "rec-01",
    policy: "Care Premier Health Assurance",
    treatment: "Total Knee Replacement",
    hospital: "Apollo Specialty Hospital (In-Network)",
    estimatedCost: 260000,
    estimatedPatientShare: 38500,
    status: "Partially Covered",
    date: "26 Sep 2026",
  },
  {
    id: "rec-02",
    policy: "Care Premier Health Assurance",
    treatment: "Cataract Surgery (Right Eye)",
    hospital: "Narayana Nethralaya (In-Network)",
    estimatedCost: 45000,
    estimatedPatientShare: 3375,
    status: "Likely Covered",
    date: "22 Sep 2026",
  },
  {
    id: "rec-03",
    policy: "Star Comprehensive Health Plan",
    treatment: "MRI Brain with Contrast",
    hospital: "Manipal Hospital Diagnostics",
    estimatedCost: 22000,
    estimatedPatientShare: 3000,
    status: "Likely Covered",
    date: "18 Sep 2026",
  },
  {
    id: "rec-04",
    policy: "Care Premier Health Assurance",
    treatment: "Bariatric Gastric Bypass",
    hospital: "Fortis Hospital Bannerghatta",
    estimatedCost: 320000,
    estimatedPatientShare: 320000,
    status: "Not Covered",
    date: "14 Sep 2026",
  },
  {
    id: "rec-05",
    policy: "HDFC ERGO Optima Secure",
    treatment: "Lap Appendectomy",
    hospital: "Max Healthcare Saket",
    estimatedCost: 110000,
    estimatedPatientShare: 14200,
    status: "Partially Covered",
    date: "09 Sep 2026",
  },
];

export const DEMO_COST_CHART_DATA = [
  { name: "Knee Replacement", total: 260000, insurer: 221500, patient: 38500 },
  { name: "Cataract", total: 45000, insurer: 41625, patient: 3375 },
  { name: "Brain MRI", total: 22000, insurer: 19000, patient: 3000 },
  { name: "Appendectomy", total: 110000, insurer: 95800, patient: 14200 },
  { name: "Angioplasty (Demo)", total: 195000, insurer: 168000, patient: 27000 },
];

export const DEMO_DASHBOARD_OVERVIEW: DashboardOverview = {
  policiesAnalyzedCount: 3,
  coverageAnalysesCount: 14,
  totalEstimatedPatientCosts: 379075,
  recentAnalyses: DEMO_RECENT_ANALYSES,
  activePolicy: DEMO_POLICY,
  costComparisonChart: DEMO_COST_CHART_DATA,
};

export const DEMO_BENCHMARK_TREATMENTS = [
  {
    treatment_id: "TRT-KNEE-01",
    treatment_name: "Total Knee Replacement (Unilateral)",
    category: "Orthopedics",
    city: "Mumbai",
    hospital_type: "Tier 1 Multi-Specialty Hospital",
    inpatient_outpatient: "inpatient",
    min_cost: 180000,
    typical_cost: 240000,
    max_cost: 320000,
    currency: "INR",
    length_of_stay_days: 4,
    description: "Unilateral total knee arthroplasty including standard implant, pre-op clearance, and acute post-op rehabilitation."
  },
  {
    treatment_id: "TRT-CATARACT-01",
    treatment_name: "Cataract Surgery with Monofocal IOL",
    category: "Ophthalmology",
    city: "Delhi NCR",
    hospital_type: "Daycare Eye Specialty Clinic",
    inpatient_outpatient: "outpatient",
    min_cost: 30000,
    typical_cost: 45000,
    max_cost: 65000,
    currency: "INR",
    length_of_stay_days: 0,
    description: "Daycare phacoemulsification with posterior chamber foldable monofocal intraocular lens."
  },
  {
    treatment_id: "TRT-ANGIO-01",
    treatment_name: "Coronary Angioplasty (PTCA with Drug-Eluting Stent)",
    category: "Cardiology",
    city: "Bengaluru",
    hospital_type: "Tertiary Cardiac Center",
    inpatient_outpatient: "inpatient",
    min_cost: 160000,
    typical_cost: 220000,
    max_cost: 310000,
    currency: "INR",
    length_of_stay_days: 3,
    description: "Percutaneous transluminal coronary angioplasty with single drug-eluting stent (DES) and ICU monitoring."
  },
  {
    treatment_id: "TRT-APP-01",
    treatment_name: "Laparoscopic Appendectomy",
    category: "General Surgery",
    city: "Hyderabad",
    hospital_type: "Multi-Specialty Hospital",
    inpatient_outpatient: "inpatient",
    min_cost: 65000,
    typical_cost: 95000,
    max_cost: 140000,
    currency: "INR",
    length_of_stay_days: 2,
    description: "Minimally invasive laparoscopic removal of vermiform appendix under general anesthesia."
  },
  {
    treatment_id: "TRT-HERNIA-01",
    treatment_name: "Laparoscopic Inguinal Hernia Repair (Mesh)",
    category: "General Surgery",
    city: "Pune",
    hospital_type: "Surgical Nursing Home",
    inpatient_outpatient: "inpatient",
    min_cost: 55000,
    typical_cost: 85000,
    max_cost: 125000,
    currency: "INR",
    length_of_stay_days: 2,
    description: "TAPP/TEP laparoscopic hernia repair using polypropylene mesh reinforcement."
  },
  {
    treatment_id: "TRT-DELIVERY-01",
    treatment_name: "Normal Vaginal Delivery",
    category: "Obstetrics & Gynecology",
    city: "Chennai",
    hospital_type: "Maternity Specialty Center",
    inpatient_outpatient: "inpatient",
    min_cost: 40000,
    typical_cost: 65000,
    max_cost: 95000,
    currency: "INR",
    length_of_stay_days: 2,
    description: "Uncomplicated normal vaginal delivery including routine intrapartum monitoring and pediatrician attendance."
  }
];

export const DEMO_CONVERSATION_SESSION = {
  id: 1,
  policyId: 1,
  title: "Knee Replacement & Room Rent Coverage Consultation",
  contextMetadata: {
    planName: "Care Premier Health Assurance Plan",
    policyNumber: "CH-2026-9812401"
  },
  createdAt: new Date(Date.now() - 3600000).toISOString(),
  updatedAt: new Date().toISOString(),
  messages: [
    {
      id: 101,
      conversationId: 1,
      role: "user" as const,
      content: "Is knee replacement surgery covered under this policy, and what out-of-pocket costs should I expect if the quote is ₹2,50,000 in Mumbai?",
      isGrounded: true,
      treatmentScenario: {
        procedureName: "Total Knee Replacement",
        hospitalQuote: 250000,
        city: "Mumbai",
        hospitalTier: "Tier 1 Multi-Specialty Hospital",
        roomTier: "Single Private Room"
      },
      evidenceReferences: [],
      createdAt: new Date(Date.now() - 1800000).toISOString()
    },
    {
      id: 102,
      conversationId: 1,
      role: "assistant" as const,
      content: "Yes, Total Knee Replacement is **covered** under Section 4.1.2 with a specific sub-limit of ₹2,50,000 and a mandatory 10% co-payment. A standard 24-month waiting period applies for pre-existing orthopedic conditions (Section 1.3). For a hospital quote of ₹2,50,000, your estimated patient responsibility is ₹40,000 (comprising ₹15,000 deductible + ₹25,000 co-payment), and the insurer covers ₹2,10,000.",
      confidence: "High",
      isGrounded: true,
      evidenceReferences: [
        {
          id: 201,
          documentSource: "Care Premier Policy Schedule 2026.pdf",
          page: 4,
          clauseSection: "Section 4.1.2 - Joint Replacement Sub-limits",
          extractedText: "Joint Replacement and Orthopedic Surgeries are admissible subject to a procedure ceiling of INR 2,50,000 per policy year and a mandatory 10% co-payment on admissible charges.",
          interpretation: "10% co-payment applies directly to admissible surgery expenses up to the ₹2,50,000 sublimit.",
          confidence: 0.98
        },
        {
          id: 202,
          documentSource: "Care Premier Policy Schedule 2026.pdf",
          page: 2,
          clauseSection: "Section 2.4 - Room Rent and Boarding Ceiling",
          extractedText: "Admissible room category is Single Private Room capped at INR 5,000 per day. Proportionate deductions apply across associated medical fees if higher tier chosen.",
          interpretation: "Staying within Single Private Room avoids proportionate deduction penalties.",
          confidence: 0.96
        }
      ],
      costEstimate: {
        treatmentName: "Total Knee Replacement (Unilateral)",
        benchmarkTreatmentId: "TRT-KNEE-01",
        currency: "INR",
        isBenchmarkMatched: true,
        benchmarkTypicalCost: 240000,
        benchmarkCostRange: { min: 180000, max: 320000 },
        estimatedTotalCost: 250000,
        potentiallyEligibleAmount: 250000,
        estimatedInsurerContribution: 210000,
        estimatedPatientResponsibility: 40000,
        deductibleApplied: 15000,
        copayApplied: 25000,
        excessOverLimit: 0,
        nonPayableExcluded: 0,
        roomRentPenalty: 0,
        confidenceLevel: "High",
        coverageStatus: "Covered with 10% Co-pay",
        drivingFactors: [
          {
            factorName: "Policy Deductible",
            impactAmount: 15000,
            description: "Annual deductible applied before insurance coverage initiates.",
            citation: "Section 1.2"
          },
          {
            factorName: "10% Procedure Co-pay",
            impactAmount: 25000,
            description: "10% mandatory co-payment on joint replacement expenses.",
            citation: "Section 4.1.2"
          },
          {
            factorName: "Benchmark Comparison",
            description: "Hospital quote of ₹2,50,000 aligns closely with Mumbai synthetic benchmark average (₹2,40,000)."
          }
        ],
        missingInformation: [],
        uncertaintyNotes: [],
        assumptions: ["Single private room ceiling adhered to", "In-network cashless pre-authorization"],
        disclaimer: "Figures are indicative simulations based on extracted policy rules and synthetic benchmark costs. Actual hospital billing and settlement depend on final discharge summary."
      },
      createdAt: new Date(Date.now() - 1790000).toISOString()
    }
  ]
};

/**
 * Mock rules engine calculation for /api/simulations.
 * Simulates backend financial calculation engine response while keeping frontend decoupled.
 */
export function calculateMockSimulation(request: SimulationRequest): SimulationResult {
  const quote = request.hospitalQuote || 0;
  const isDeluxePenalty = request.roomCategory?.includes("Deluxe") || false;
  const roomRentPenaltyAmount = isDeluxePenalty ? Math.round(quote * 0.12) : 0;

  // In-network contracted rate is ~90% of billed quote
  const contractedAllowance = Math.round(quote * 0.9);
  const consumables = request.consumablesEstimate || 0;
  const nonPayableTotal = consumables + roomRentPenaltyAmount;

  const deductiblePaid = Math.min(request.deductible || 0, contractedAllowance);
  const remainingAdmissible = Math.max(0, contractedAllowance - deductiblePaid);
  const copayPaid = Math.round(remainingAdmissible * ((request.copayPercent || 0) / 100));

  const potentialInsurer = Math.max(0, remainingAdmissible - copayPaid);
  const limit = request.coverageLimit || Infinity;
  const insuranceShare = Math.min(potentialInsurer, limit);

  const overflowBeyondLimit = Math.max(0, potentialInsurer - limit);
  const patientShare = deductiblePaid + copayPaid + nonPayableTotal + overflowBeyondLimit;
  const effectivePercent = quote > 0 ? Math.round((insuranceShare / quote) * 100) : 0;

  return {
    totalCost: quote,
    contractedAllowance,
    insuranceShare,
    patientShare,
    deductiblePaid,
    copayPaid,
    nonPayableTotal,
    roomRentPenaltyAmount,
    effectivePercent,
    isLimitReached: potentialInsurer > limit,
    currency: "INR",
    calculatedAt: new Date().toISOString(),
    rulesEngineVersion: "v2.4-deterministic-preview",
  };
}
