/**
 * Data classification tiers ensuring clear distinction between
 * verified policy sources, AI inferences, deterministic calculations, and provisional estimates.
 */
export type DataSourceTier =
  | "policy_source"
  | "ai_interpretation"
  | "deterministic_calc"
  | "estimated_result";

export interface DataSourceMeta {
  tier: DataSourceTier;
  label: string;
  shortLabel: string;
  description: string;
  sourceDocName?: string;
  clauseReference?: string;
  confidenceScore?: number;
}

export type StatusVariant =
  | "policy_source"
  | "ai_interpretation"
  | "deterministic_calc"
  | "estimated"
  | "estimated_result"
  | "covered"
  | "partial"
  | "not_determined"
  | "warning"
  | "error"
  | "neutral";

export type CoverageStatus =
  | "Likely Covered"
  | "Partially Covered"
  | "Not Determined"
  | "Not Covered";

export interface MetricCardData {
  id: string;
  label: string;
  value: string | number;
  prefix?: string;
  suffix?: string;
  subtext?: string;
  sourceTier: DataSourceTier;
  trend?: {
    direction: "up" | "down" | "neutral";
    text: string;
  };
  highlight?: boolean;
}

export interface NavItem {
  label: string;
  href: string;
  badge?: string;
  isExternal?: boolean;
}

// ==========================================
// BACKEND DOMAIN CONTRACT TYPES
// ==========================================

/**
 * Standardized API Error representation
 */
export interface ApiError {
  statusCode: number;
  message: string;
  code?: string;
  details?: string | Record<string, unknown>;
  timestamp: string;
}

/**
 * Verifiable Evidence Reference linked to policy source documents
 */
export interface EvidenceReference {
  id: string;
  title: string;
  sourceDoc: string;
  pageNumber: string;
  clauseReference: string;
  sourceText: string;
  aiInterpretation: string;
  deterministicRule: string;
  calculationImpact: string;
  confidence: number;
  category: string;
}

// Backwards compatibility alias
export type EvidenceItem = EvidenceReference;

/**
 * Policy Rule Clause entity
 */
export interface CoverageRule {
  id: string;
  category: string;
  ruleName: string;
  description: string;
  admissibilityStatus: "Covered" | "Partial" | "Excluded" | "Not Determined";
  sublimit?: string;
  copayPercent?: number;
  waitingPeriodMonths?: number;
  clauseCitation?: string;
}

/**
 * High-level policy summary returned by /api/policies/{id}
 */
export interface PolicySummary {
  id: string;
  planName: string;
  insurerName: string;
  policyNumber: string;
  policyPeriod: string;
  sumInsured: number | null;
  deductible: number | null;
  copayPercent: number | null;
  roomRentLimit: string;
  roomRentCondition: string;
  networkType: string;
  waitingPeriodMonths: number | null;
  categories: {
    name: string;
    status: string;
    sublimit?: string;
  }[];
}

/**
 * Full Policy Entity
 */
export interface Policy extends PolicySummary {
  uploadedAt: string;
  documentFileName: string;
  documentFileSizeBytes: number;
  ocrConfidence: number;
  rules: CoverageRule[];
}

/**
 * Treatment entity
 */
export interface Treatment {
  id: string;
  name: string;
  category: string;
  cptCode?: string;
  typicalCostRange?: {
    min: number;
    max: number;
    currency: string;
  };
}

/**
 * Analysis request payload to POST /api/analyses
 */
export interface AnalysisRequest {
  policyId: string;
  treatmentName: string;
  cptCode?: string;
  estimatedHospitalQuote?: number;
  roomCategory?: string;
}

/**
 * Coverage analysis result returned by POST /api/analyses or GET /api/analyses/{id}
 */
export interface AnalysisResult {
  id: string;
  policyId: string;
  treatmentName: string;
  treatmentCategory: string;
  cptCode?: string;
  coverageStatus: CoverageStatus;
  coveragePercentage: number | null;
  estimatedTotalCost: number | null;
  estimatedInsuranceShare: number | null;
  estimatedPatientShare: number | null;
  deductibleApplicable: number | null;
  copayAmount: number | null;
  sublimitApplied?: number | null;
  nonPayableConsumables: number | null;
  waitingPeriodStatus: string;
  roomRuleApplied: string;
  exclusionsList: string[];
  evidenceList: EvidenceReference[];
  evaluatedAt: string;
}

// Backwards compatibility alias
export type CoverageAnalysis = AnalysisResult;

/**
 * Simulation request payload to POST /api/simulations
 */
export interface SimulationRequest {
  policyId?: string;
  treatment: string;
  hospitalQuote: number;
  roomCategory: string;
  deductible: number;
  copayPercent: number;
  coverageLimit: number;
  consumablesEstimate: number;
}

/**
 * Simulation calculation result returned by backend rules engine
 */
export interface SimulationResult {
  totalCost: number;
  contractedAllowance: number;
  insuranceShare: number;
  patientShare: number;
  deductiblePaid: number;
  copayPaid: number;
  nonPayableTotal: number;
  roomRentPenaltyAmount: number;
  effectivePercent: number;
  isLimitReached: boolean;
  currency: string;
  calculatedAt: string;
  rulesEngineVersion: string;
}

// Legacy alias
export type SimulatorInputs = SimulationRequest;
export type SimulatorResult = SimulationResult;

/**
 * Dashboard record model
 */
export interface RecentAnalysisRecord {
  id: string;
  policy: string;
  treatment: string;
  hospital: string;
  estimatedCost: number | null;
  estimatedPatientShare: number | null;
  status: CoverageStatus;
  date: string;
}

/**
 * Dashboard Overview payload
 */
export interface DashboardOverview {
  policiesAnalyzedCount: number;
  coverageAnalysesCount: number;
  totalEstimatedPatientCosts: number;
  recentAnalyses: RecentAnalysisRecord[];
  activePolicy: PolicySummary | null;
  costComparisonChart: {
    name: string;
    total: number;
    insurer: number;
    patient: number;
  }[];
}
