import {
  Policy,
  PolicySummary,
  CoverageRule,
  AnalysisRequest,
  AnalysisResult,
  SimulationRequest,
  SimulationResult,
  DashboardOverview,
  RecentAnalysisRecord,
  ConversationSession,
  ConversationMessage,
  ConversationEvidence,
  TreatmentEstimateData,
  WhatIfComparisonData,
  CoverageStatus,
  EvidenceReference,
  User,
  AuthResponse,
  ApiError,
} from "@/types";
import { parseApiError, createHttpError, CoverWiseApiError } from "./errors";
/**
 * Base API URL configured via environment variable or default local backend.
 */
const API_BASE_URL = (
  process.env.NEXT_PUBLIC_API_URL !== undefined && process.env.NEXT_PUBLIC_API_URL !== ""
    ? process.env.NEXT_PUBLIC_API_URL
    : typeof window !== "undefined"
    ? ""
    : "http://localhost:8000"
).replace(/\/+$/, "");

const DEFAULT_TIMEOUT_MS = 15000;

let authToken: string | null = null;

export function setApiAuthToken(token: string | null) {
  authToken = token;
  if (typeof window !== "undefined") {
    if (token) {
      localStorage.setItem("coverwise_token", token);
    } else {
      localStorage.removeItem("coverwise_token");
    }
  }
}

export function getApiAuthToken(): string | null {
  if (authToken) return authToken;
  if (typeof window !== "undefined") {
    authToken = localStorage.getItem("coverwise_token");
  }
  return authToken;
}

/**
 * Helper to handle fetch with timeout, auth token injection, and standard status code validation.
 */
async function fetchWithTimeout(
  url: string,
  options: RequestInit = {},
  timeoutMs: number = DEFAULT_TIMEOUT_MS
): Promise<Response> {
  const controller = new AbortController();
  const id = setTimeout(() => controller.abort(), timeoutMs);

  const headers: Record<string, string> = {
    Accept: "application/json",
    ...((options.headers as Record<string, string>) || {}),
  };
  const token = getApiAuthToken();
  if (token && !headers["Authorization"]) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  try {
    const response = await fetch(url, {
      ...options,
      signal: controller.signal,
      headers,
    });
    clearTimeout(id);
    return response;
  } catch (error) {
    clearTimeout(id);
    throw error;
  }
}

/**
 * Handles standard JSON response and maps non-2xx status codes to CoverWiseApiError.
 */
async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    let errorPayload: { message?: string; detail?: string; code?: string } = {};
    try {
      errorPayload = await response.json();
    } catch {
      // Body is not JSON
    }

    const message =
      errorPayload.message ||
      (typeof errorPayload.detail === "string" ? errorPayload.detail : undefined);

    throw createHttpError(response.status, message, errorPayload);
  }

  return (await response.json()) as T;
}

// ==========================================
// API CLIENT IMPLEMENTATION
// ==========================================

export const api = {
  /**
   * POST /api/auth/register
   * Registers a new user account and stores JWT session token.
   */
  async register(email: string, password: string, fullName?: string): Promise<AuthResponse> {
    try {
      const res = await fetchWithTimeout(`${API_BASE_URL}/api/auth/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email,
          password,
          full_name: fullName,
        }),
      });
      const data = await handleResponse<{
        access_token: string;
        token_type: string;
        user: { id: number; email: string; full_name?: string; is_active: boolean };
      }>(res);
      setApiAuthToken(data.access_token);
      return {
        accessToken: data.access_token,
        tokenType: data.token_type,
        user: {
          id: data.user.id,
          email: data.user.email,
          fullName: data.user.full_name,
          isActive: data.user.is_active,
        },
      };
    } catch (err) {
      throw parseApiError(err);
    }
  },

  /**
   * POST /api/auth/login
   * Authenticates user credentials and stores JWT session token.
   */
  async login(email: string, password: string): Promise<AuthResponse> {
    try {
      const res = await fetchWithTimeout(`${API_BASE_URL}/api/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });
      const data = await handleResponse<{
        access_token: string;
        token_type: string;
        user: { id: number; email: string; full_name?: string; is_active: boolean };
      }>(res);
      setApiAuthToken(data.access_token);
      return {
        accessToken: data.access_token,
        tokenType: data.token_type,
        user: {
          id: data.user.id,
          email: data.user.email,
          fullName: data.user.full_name,
          isActive: data.user.is_active,
        },
      };
    } catch (err) {
      throw parseApiError(err);
    }
  },

  /**
   * GET /api/auth/me
   * Fetches profile of currently authenticated user.
   */
  async getCurrentUser(): Promise<User> {
    try {
      const res = await fetchWithTimeout(`${API_BASE_URL}/api/auth/me`, {
        method: "GET",
      });
      const data = await handleResponse<{
        id: number;
        email: string;
        full_name?: string;
        is_active: boolean;
        created_at?: string;
        updated_at?: string;
      }>(res);
      return {
        id: data.id,
        email: data.email,
        fullName: data.full_name,
        isActive: data.is_active,
        createdAt: data.created_at,
        updatedAt: data.updated_at,
      };
    } catch (err) {
      throw parseApiError(err);
    }
  },

  /**
   * POST /api/auth/logout
   * Clears session and removes stored access token.
   */
  async logout(): Promise<{ message: string }> {
    try {
      const res = await fetchWithTimeout(`${API_BASE_URL}/api/auth/logout`, {
        method: "POST",
      });
      setApiAuthToken(null);
      return await handleResponse<{ message: string }>(res);
    } catch {
      setApiAuthToken(null);
      return { message: "Successfully logged out." };
    }
  },

  /**
   * GET /api/health
   * Verifies API server and extraction engine availability.
   */
  async getHealth(): Promise<{ status: string; version: string; service: string }> {
    try {
      const res = await fetchWithTimeout(`${API_BASE_URL}/api/health`, { method: "GET" });
      return await handleResponse<{ status: string; version: string; service: string }>(res);
    } catch (err) {
      throw parseApiError(err);
    }
  },

  /**
   * POST /api/policies/upload
   * Ingests a policy document (PDF/Image) and initiates OCR / semantic extraction.
   */
  async uploadPolicy(
    file: File | { name: string; size: number; type: string }
  ): Promise<PolicySummary> {
    try {
      const formData = new FormData();
      if (file instanceof File) {
        formData.append("file", file);
      } else {
        // Construct fallback blob if mock object passed
        formData.append("file", new Blob(["mock"], { type: file.type }), file.name);
      }

      const res = await fetchWithTimeout(`${API_BASE_URL}/api/policies/upload`, {
        method: "POST",
        body: formData,
      });

      const raw = await handleResponse<Record<string, unknown>>(res);
      const id = String(raw.id);
      if (typeof window !== "undefined") {
        localStorage.setItem("coverwise_active_policy_id", id);
      }

      return normalizePolicy(raw);
    } catch (err) {
      throw parseApiError(err);
    }
  },

  /**
   * GET /api/policies/{id}
   * Fetches full extracted policy entity with rule clauses.
   */
  async getPolicyById(id: string): Promise<Policy> {
    try {
      const res = await fetchWithTimeout(`${API_BASE_URL}/api/policies/${encodeURIComponent(id)}`, {
        method: "GET",
      });
      const raw = await handleResponse<Record<string, unknown>>(res);
      return normalizePolicy(raw);
    } catch (err) {
      throw parseApiError(err);
    }
  },

  /**
   * GET /api/policies
   * Lists all uploaded policies for the current user.
   */
  async getPolicies(): Promise<PolicySummary[]> {
    try {
      const res = await fetchWithTimeout(`${API_BASE_URL}/api/policies`, {
        method: "GET",
      });
      const list = await handleResponse<Record<string, unknown>[]>(res);
      return (list || []).map(normalizePolicy);
    } catch (err) {
      throw parseApiError(err);
    }
  },

  /**
   * GET /api/policies/active
   * Retrieves the currently active policy for the authenticated user.
   */
  async getActivePolicy(): Promise<Policy | null> {
    try {
      const res = await fetchWithTimeout(`${API_BASE_URL}/api/policies/active`, {
        method: "GET",
      });
      if (res.status === 404) return null;
      const raw = await handleResponse<Record<string, unknown>>(res);
      return normalizePolicy(raw);
    } catch (err) {
      const parsed = parseApiError(err);
      if (parsed.statusCode === 404) return null;
      throw parsed;
    }
  },

  /**
   * POST /api/policies/{id}/activate
   * Sets a policy as the active policy for all subsequent calculations.
   */
  async activatePolicy(id: string | number): Promise<Policy> {
    try {
      const res = await fetchWithTimeout(`${API_BASE_URL}/api/policies/${encodeURIComponent(String(id))}/activate`, {
        method: "POST",
      });
      const raw = await handleResponse<Record<string, unknown>>(res);
      if (typeof window !== "undefined") {
        localStorage.setItem("coverwise_active_policy_id", String(id));
      }
      return normalizePolicy(raw);
    } catch (err) {
      throw parseApiError(err);
    }
  },

  /**
   * GET /api/coverage
   * Lists contractual coverage rules for a policy.
   */
  async getCoverageRules(policyId?: string | number): Promise<CoverageRule[]> {
    try {
      const q = policyId ? `?policy_id=${encodeURIComponent(String(policyId))}` : "";
      const res = await fetchWithTimeout(`${API_BASE_URL}/api/coverage${q}`, {
        method: "GET",
      });
      const list = await handleResponse<Record<string, unknown>[]>(res);
      return (list || []).map((r, idx) => ({
        id: String(r.id || `rule-${idx}`),
        category: String(r.category || "General"),
        ruleName: String(r.procedure_name || r.rule_name || r.source_reference || "Coverage Rule"),
        description: String(r.waiting_period || r.conditions || r.network_condition || "Contractual Rule"),
        admissibilityStatus:
          r.coverage_status === "covered"
            ? "Covered"
            : r.coverage_status === "partially_covered"
            ? "Partial"
            : r.coverage_status === "not_covered"
            ? "Excluded"
            : "Not Determined",
        sublimit: r.coverage_limit_amount
          ? `Up to ₹${Number(r.coverage_limit_amount).toLocaleString()}`
          : r.coverage_limit
          ? `Up to ₹${Number(r.coverage_limit).toLocaleString()}`
          : undefined,
        copayPercent: typeof r.copay_percentage === "number" ? r.copay_percentage : undefined,
        clauseCitation: typeof r.source_reference === "string" ? r.source_reference : undefined,
      }));
    } catch (err) {
      throw parseApiError(err);
    }
  },

  /**
   * POST /api/analyses
   * Submits a treatment query against a policy to produce coverage intelligence.
   */
  async createAnalysis(request: AnalysisRequest): Promise<AnalysisResult> {
    try {
      const numericPolicyId =
        typeof request.policyId === "string"
          ? parseInt(request.policyId, 10)
          : request.policyId;
      if (!numericPolicyId || isNaN(numericPolicyId)) {
        throw new Error("A valid policy ID is required to run analysis.");
      }
      const payload = {
        policy_id: numericPolicyId,
        treatment_name: request.treatmentName,
      };
      const res = await fetchWithTimeout(`${API_BASE_URL}/api/analyses`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await handleResponse<Record<string, unknown>>(res);
      return normalizeAnalysisResult(data);
    } catch (err) {
      throw parseApiError(err);
    }
  },

  /**
   * GET /api/analyses/{id}
   * Retrieves an existing coverage analysis by ID.
   */
  async getAnalysisById(id: string): Promise<AnalysisResult> {
    try {
      const res = await fetchWithTimeout(`${API_BASE_URL}/api/analyses/${encodeURIComponent(id)}`, {
        method: "GET",
      });
      const data = await handleResponse<Record<string, unknown>>(res);
      return normalizeAnalysisResult(data);
    } catch (err) {
      throw parseApiError(err);
    }
  },

  /**
   * POST /api/simulations
   * Submits cost parameters to backend rules engine to evaluate patient vs. insurer liability.
   * Keeps calculations decoupled from the frontend.
   */
  async createSimulation(request: SimulationRequest): Promise<SimulationResult> {
    try {
      const res = await fetchWithTimeout(`${API_BASE_URL}/api/simulations`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(request),
      });
      const raw = await handleResponse<Record<string, unknown>>(res);
      return normalizeSimulationResult(raw);
    } catch (err) {
      throw parseApiError(err);
    }
  },

  /**
   * GET /api/dashboard/overview
   * Fetches summary statistics and recent analyses for the intelligence dashboard.
   */
  async getDashboardOverview(policyId?: number | string): Promise<DashboardOverview> {
    try {
      const q = policyId ? `?policy_id=${encodeURIComponent(String(policyId))}` : "";
      const res = await fetchWithTimeout(`${API_BASE_URL}/api/dashboard${q}`, {
        method: "GET",
      });
      const raw = await handleResponse<Record<string, unknown>>(res);
      return normalizeDashboard(raw);
    } catch (err) {
      throw parseApiError(err);
    }
  },

  /**
   * GET /api/analyses/recent
   * Fetches the user's recent policy analyses.
   */
  async getRecentAnalyses(): Promise<RecentAnalysisRecord[]> {
    try {
      const res = await fetchWithTimeout(`${API_BASE_URL}/api/analyses/recent`, {
        method: "GET",
      });
      return await handleResponse<RecentAnalysisRecord[]>(res);
    } catch (err) {
      throw parseApiError(err);
    }
  },

  /**
   * POST /api/conversations
   * Initializes a conversational session for an ingested policy.
   */
  async createConversation(
    policyId: number | string,
    initialQuestion?: string,
    title?: string
  ): Promise<ConversationSession> {
    try {
      const numericPolicyId =
        typeof policyId === "string"
          ? parseInt(policyId, 10)
          : policyId;
      if (!numericPolicyId || isNaN(numericPolicyId)) {
        throw new Error("A valid policy ID is required to create a conversation.");
      }
      const res = await fetchWithTimeout(`${API_BASE_URL}/api/conversations`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          policy_id: numericPolicyId,
          title,
          initial_message: initialQuestion,
        }),
      });
      const data = await handleResponse<Record<string, unknown>>(res);
      return normalizeSession(data);
    } catch (err) {
      throw parseApiError(err);
    }
  },

  /**
   * GET /api/conversations/{id}
   * Fetches an active conversation and its message turns.
   */
  async getConversation(conversationId: number | string): Promise<ConversationSession> {
    try {
      const res = await fetchWithTimeout(
        `${API_BASE_URL}/api/conversations/${encodeURIComponent(conversationId)}`,
        { method: "GET" }
      );
      const data = await handleResponse<Record<string, unknown>>(res);
      return normalizeSession(data);
    } catch (err) {
      throw parseApiError(err);
    }
  },

  /**
   * POST /api/conversations/{id}/messages
   * Sends a follow-up question or scenario to the assistant.
   */
  async sendMessage(
    conversationId: number | string,
    content: string,
    treatmentScenario?: Record<string, unknown>
  ): Promise<ConversationMessage> {
    try {
      const res = await fetchWithTimeout(
        `${API_BASE_URL}/api/conversations/${encodeURIComponent(conversationId)}/messages`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            content,
            treatment_scenario: treatmentScenario,
          }),
        }
      );
      const data = await handleResponse<Record<string, unknown>>(res);
      return normalizeMessage(data);
    } catch (err) {
      throw parseApiError(err);
    }
  },

  /**
   * GET /api/conversations/policy/{policy_id}
   * Retrieves conversation sessions associated with a policy.
   */
  async getPolicyConversations(policyId: number | string): Promise<ConversationSession[]> {
    try {
      const res = await fetchWithTimeout(
        `${API_BASE_URL}/api/conversations/policy/${encodeURIComponent(policyId)}`,
        { method: "GET" }
      );
      const data = await handleResponse<Record<string, unknown>[]>(res);
      return (data || []).map(normalizeSession);
    } catch (err) {
      throw parseApiError(err);
    }
  },

  /**
   * POST /api/treatment-estimates
   * Computes deterministic out-of-pocket and insurer contribution.
   */
  async estimateTreatmentCost(params: {
    policyId: number | string;
    procedureName: string;
    hospitalQuote?: number;
    hospitalTier?: string;
    city?: string;
    isNetworkHospital?: boolean;
    roomTier?: string;
    lengthOfStayDays?: number;
    patientAge?: number;
    diagnosis?: string;
    preExistingCondition?: boolean;
  }): Promise<TreatmentEstimateData> {
    try {
      const numericPolicyId =
        typeof params.policyId === "string"
          ? parseInt(params.policyId, 10)
          : params.policyId;
      if (!numericPolicyId || isNaN(numericPolicyId)) {
        throw new Error("A valid policy ID is required to estimate treatment cost.");
      }
      const res = await fetchWithTimeout(`${API_BASE_URL}/api/treatment-estimates`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          policy_id: numericPolicyId,
          procedure_name: params.procedureName,
          hospital_quote: params.hospitalQuote,
          hospital_tier: params.hospitalTier,
          city: params.city,
          is_network_hospital: params.isNetworkHospital ?? true,
          room_tier: params.roomTier,
          length_of_stay_days: params.lengthOfStayDays,
          patient_age: params.patientAge,
          diagnosis: params.diagnosis,
          pre_existing_condition: params.preExistingCondition ?? false,
        }),
      });
      const data = await handleResponse<Record<string, unknown>>(res);
      return normalizeEstimate(data);
    } catch (err) {
      throw parseApiError(err);
    }
  },

  /**
   * POST /api/treatment-estimates/what-if
   * Evaluates cost impact when scenario parameters change.
   */
  async evaluateWhatIf(params: {
    policyId: number | string;
    previousScenario: Record<string, unknown>;
    updatedScenario: Record<string, unknown>;
  }): Promise<WhatIfComparisonData> {
    try {
      const numericPolicyId =
        typeof params.policyId === "string"
          ? parseInt(params.policyId, 10)
          : params.policyId;
      if (!numericPolicyId || isNaN(numericPolicyId)) {
        throw new Error("A valid policy ID is required to evaluate What-If scenario.");
      }
      const res = await fetchWithTimeout(`${API_BASE_URL}/api/treatment-estimates/what-if`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          policy_id: numericPolicyId,
          previous_scenario: params.previousScenario,
          updated_scenario: params.updatedScenario,
        }),
      });
      const data = await handleResponse<Record<string, unknown>>(res);
      return normalizeWhatIf(data);
    } catch (err) {
      throw parseApiError(err);
    }
  },

  /**
   * GET /api/treatment-estimates/benchmarks
   * Retrieves synthetic cost benchmark records.
   */
  async getBenchmarkTreatments(search?: string, city?: string): Promise<Record<string, unknown>[]> {
    try {
      const queryParams = new URLSearchParams();
      if (search) queryParams.set("search", search);
      if (city) queryParams.set("city", city);

      const qs = queryParams.toString() ? `?${queryParams.toString()}` : "";
      const res = await fetchWithTimeout(`${API_BASE_URL}/api/treatment-estimates/benchmarks${qs}`, {
        method: "GET",
      });
      return await handleResponse<Record<string, unknown>[]>(res);
    } catch (err) {
      throw parseApiError(err);
    }
  },
};

// ==========================================
// NORMALIZATION HELPERS
// ==========================================

function normalizeEvidence(raw: Record<string, unknown> | null | undefined): ConversationEvidence {
  if (!raw) {
    return {
      documentSource: "Policy Document",
    };
  }
  return {
    id: typeof raw.id === "number" ? raw.id : undefined,
    documentSource: String(raw.document_source || raw.documentSource || "Policy Document"),
    page: typeof raw.page === "number" ? raw.page : undefined,
    clauseSection: typeof (raw.clause_section || raw.clauseSection) === "string" ? String(raw.clause_section || raw.clauseSection) : undefined,
    extractedText: typeof (raw.extracted_text || raw.extractedText) === "string" ? String(raw.extracted_text || raw.extractedText) : undefined,
    interpretation: typeof raw.interpretation === "string" ? raw.interpretation : undefined,
    confidence: typeof raw.confidence === "number" ? raw.confidence : undefined,
  };
}

function normalizeEstimate(raw: Record<string, unknown> | null | undefined): TreatmentEstimateData {
  if (!raw) {
    return {
      treatmentName: "Treatment",
      currency: "INR",
      isBenchmarkMatched: false,
      estimatedTotalCost: 0,
      potentiallyEligibleAmount: 0,
      estimatedInsurerContribution: 0,
      estimatedPatientResponsibility: 0,
      deductibleApplied: 0,
      copayApplied: 0,
      excessOverLimit: 0,
      nonPayableExcluded: 0,
      roomRentPenalty: 0,
      confidenceLevel: "High",
      coverageStatus: "Covered",
      drivingFactors: [],
      missingInformation: [],
      uncertaintyNotes: [],
      assumptions: [],
      disclaimer: "Estimates are indicative and based on extracted policy rules.",
    };
  }
  const rawFactors = (raw.driving_factors || raw.drivingFactors) as Record<string, unknown>[] | undefined;
  return {
    treatmentName: String(raw.treatment_name || raw.treatmentName || "Treatment"),
    benchmarkTreatmentId: typeof (raw.benchmark_treatment_id || raw.benchmarkTreatmentId) === "string" ? String(raw.benchmark_treatment_id || raw.benchmarkTreatmentId) : undefined,
    currency: String(raw.currency || "INR"),
    isBenchmarkMatched: Boolean(raw.is_benchmark_matched ?? raw.isBenchmarkMatched ?? false),
    benchmarkTypicalCost: typeof (raw.benchmark_typical_cost ?? raw.benchmarkTypicalCost) === "number" ? Number(raw.benchmark_typical_cost ?? raw.benchmarkTypicalCost) : undefined,
    benchmarkCostRange: (raw.benchmark_cost_range || raw.benchmarkCostRange) as { min: number; max: number } | undefined,
    estimatedTotalCost: Number(raw.estimated_total_cost ?? raw.estimatedTotalCost ?? 0),
    potentiallyEligibleAmount: Number(raw.potentially_eligible_amount ?? raw.potentiallyEligibleAmount ?? 0),
    estimatedInsurerContribution: Number(raw.estimated_insurer_contribution ?? raw.estimatedInsurerContribution ?? 0),
    estimatedPatientResponsibility: Number(raw.estimated_patient_responsibility ?? raw.estimatedPatientResponsibility ?? 0),
    deductibleApplied: Number(raw.deductible_applied ?? raw.deductibleApplied ?? 0),
    deductibleStatus: String(raw.deductible_status || raw.deductibleStatus || "determined"),
    deductibleAmount:
      raw.deductible_status === "not_determined"
        ? null
        : raw.deductible_amount != null
        ? Number(raw.deductible_amount)
        : raw.deductibleAmount != null
        ? Number(raw.deductibleAmount)
        : null,
    isConditionalOnDeductible: Boolean(
      raw.is_conditional_on_deductible ??
      raw.isConditionalOnDeductible ??
      (raw.deductible_status === "not_determined")
    ),
    policyCoveragePercentage:
      raw.policy_coverage_percentage != null
        ? Number(raw.policy_coverage_percentage)
        : raw.policyCoveragePercentage != null
        ? Number(raw.policyCoveragePercentage)
        : null,
    policyCoverageCap:
      raw.policy_coverage_cap != null
        ? Number(raw.policy_coverage_cap)
        : raw.policyCoverageCap != null
        ? Number(raw.policyCoverageCap)
        : null,
    copayApplied: Number(raw.copay_applied ?? raw.copayApplied ?? 0),
    applicableCopayPercentage: raw.applicable_copay_percentage != null ? Number(raw.applicable_copay_percentage) : (raw.applicableCopayPercentage != null ? Number(raw.applicableCopayPercentage) : null),
    excessOverLimit: Number(raw.excess_over_limit ?? raw.excessOverLimit ?? 0),
    nonPayableExcluded: Number(raw.non_payable_excluded ?? raw.nonPayableExcluded ?? 0),
    roomRentPenalty: Number(raw.room_rent_penalty ?? raw.roomRentPenalty ?? 0),
    calculationTrace: Array.isArray(raw.calculation_trace || raw.calculationTrace) ? ((raw.calculation_trace || raw.calculationTrace) as string[]) : [],
    confidenceLevel: String(raw.confidence_level || raw.confidenceLevel || "High"),
    coverageStatus: String(raw.coverage_status || raw.coverageStatus || "Covered"),
    drivingFactors: (rawFactors || []).map((f) => ({
      factorName: String(f.factor_name || f.factorName || ""),
      impactAmount: typeof (f.impact_amount ?? f.impactAmount) === "number" ? Number(f.impact_amount ?? f.impactAmount) : undefined,
      description: String(f.description || ""),
      citation: typeof f.citation === "string" ? f.citation : undefined,
    })),
    missingInformation: Array.isArray(raw.missing_information || raw.missingInformation) ? ((raw.missing_information || raw.missingInformation) as string[]) : [],
    uncertaintyNotes: Array.isArray(raw.uncertainty_notes || raw.uncertaintyNotes) ? ((raw.uncertainty_notes || raw.uncertaintyNotes) as string[]) : [],
    assumptions: Array.isArray(raw.assumptions) ? (raw.assumptions as string[]) : [],
    disclaimer: String(raw.disclaimer || "Estimates are indicative and based on extracted policy rules."),
    rawCalculation: (raw.raw_calculation || raw.rawCalculation) as Record<string, unknown> | undefined,
  };
}

function normalizeMessage(raw: Record<string, unknown>): ConversationMessage {
  const evRefs = (raw.evidence_references || raw.evidenceReferences) as Record<string, unknown>[] | undefined;
  const costEst = (raw.cost_estimate || raw.costEstimate) as Record<string, unknown> | undefined;
  return {
    id: Number(raw.id || 0),
    conversationId: Number(raw.conversation_id ?? raw.conversationId ?? 0),
    role: (raw.role as "user" | "assistant" | "system") || "assistant",
    content: String(raw.content || ""),
    confidence: typeof raw.confidence === "string" ? raw.confidence : undefined,
    isGrounded: Boolean(raw.is_grounded ?? raw.isGrounded ?? true),
    uncertaintyReason: typeof (raw.uncertainty_reason || raw.uncertaintyReason) === "string" ? String(raw.uncertainty_reason || raw.uncertaintyReason) : undefined,
    missingInformation: Array.isArray(raw.missing_information || raw.missingInformation) ? ((raw.missing_information || raw.missingInformation) as string[]) : [],
    treatmentScenario: (raw.treatment_scenario || raw.treatmentScenario) as Record<string, unknown> | undefined,
    costEstimate: costEst ? normalizeEstimate(costEst) : undefined,
    evidenceReferences: (evRefs || []).map(normalizeEvidence),
    createdAt: String(raw.created_at || raw.createdAt || new Date().toISOString()),
  };
}

function normalizeSession(raw: Record<string, unknown>): ConversationSession {
  const msgs = (raw.messages || []) as Record<string, unknown>[];
  return {
    id: Number(raw.id || 0),
    policyId: Number(raw.policy_id ?? raw.policyId ?? 0),
    title: typeof raw.title === "string" ? raw.title : undefined,
    contextMetadata: (raw.context_metadata || raw.contextMetadata) as Record<string, unknown> | undefined,
    messages: msgs.map(normalizeMessage),
    createdAt: String(raw.created_at || raw.createdAt || new Date().toISOString()),
    updatedAt: String(raw.updated_at || raw.updatedAt || new Date().toISOString()),
  };
}

function normalizeWhatIf(raw: Record<string, unknown>): WhatIfComparisonData {
  return {
    previousScenario: (raw.previous_scenario || raw.previousScenario || {}) as Record<string, unknown>,
    updatedScenario: (raw.updated_scenario || raw.updatedScenario || {}) as Record<string, unknown>,
    previousEstimate: normalizeEstimate((raw.previous_estimate || raw.previousEstimate) as Record<string, unknown>),
    updatedEstimate: normalizeEstimate((raw.updated_estimate || raw.updatedEstimate) as Record<string, unknown>),
    changesDetected: Array.isArray(raw.changes_detected || raw.changesDetected) ? ((raw.changes_detected || raw.changesDetected) as string[]) : [],
    totalCostDelta: Number(raw.total_cost_delta ?? raw.totalCostDelta ?? 0),
    insurerContributionDelta: Number(raw.insurer_contribution_delta ?? raw.insurerContributionDelta ?? 0),
    patientResponsibilityDelta: Number(raw.patient_responsibility_delta ?? raw.patientResponsibilityDelta ?? 0),
    explanationOfChanges: Array.isArray(raw.explanation_of_changes || raw.explanationOfChanges) ? ((raw.explanation_of_changes || raw.explanationOfChanges) as string[]) : [],
  };
}

function normalizeAnalysisResult(raw: Record<string, unknown>): AnalysisResult {
  const coverageStatusRaw = String(raw.coverage_status || raw.coverageStatus || "not_determined");
  let status: CoverageStatus = "Not Determined";
  if (coverageStatusRaw === "likely_covered" || coverageStatusRaw === "Likely Covered") {
    status = "Likely Covered";
  } else if (
    coverageStatusRaw === "partially_covered" ||
    coverageStatusRaw === "Partially Covered" ||
    coverageStatusRaw === "Partial"
  ) {
    status = "Partially Covered";
  } else if (coverageStatusRaw === "not_covered" || coverageStatusRaw === "Not Covered") {
    status = "Not Covered";
  }

  const rawEvidence = (raw.evidence_references || raw.evidenceList || []) as Record<string, unknown>[];
  const evidenceList: EvidenceReference[] = rawEvidence.map((ev, idx) => ({
    id: String(ev.id || `ev-${idx}`),
    title: String(ev.clause_section || ev.title || "Policy Provision"),
    sourceDoc: String(ev.document_source || ev.sourceDoc || "Policy Schedule"),
    pageNumber: String(ev.page ?? ev.pageNumber ?? "1"),
    clauseReference: String(ev.clause_section || ev.clauseReference || "Section 3.1"),
    sourceText: String(ev.extracted_text || ev.sourceText || ""),
    aiInterpretation: String(ev.interpretation || ev.aiInterpretation || ""),
    deterministicRule: String(ev.deterministic_rule || ev.deterministicRule || "Standard Benefit Clause"),
    calculationImpact: String(ev.calculation_impact || ev.calculationImpact || "Eligible for coverage"),
    confidence: Number(ev.confidence ?? 0.85),
    category: String(ev.category || "Hospitalization"),
  }));

  return {
    id: String(raw.id ?? ""),
    policyId: String(raw.policy_id ?? raw.policyId ?? ""),
    treatmentName: String(raw.treatment_name ?? raw.treatmentName ?? "Treatment"),
    treatmentCategory: String(raw.treatment_category ?? raw.treatmentCategory ?? "Inpatient Care"),
    cptCode: typeof raw.cpt_code === "string" ? raw.cpt_code : (typeof raw.cptCode === "string" ? raw.cptCode : undefined),
    coverageStatus: status,
    coveragePercentage:
      raw.coverage_percentage != null
        ? Number(raw.coverage_percentage)
        : raw.coverage_limit_percentage_of_si != null
        ? Number(raw.coverage_limit_percentage_of_si)
        : raw.coveragePercentage != null
        ? Number(raw.coveragePercentage)
        : raw.coverage_percentage_or_cap != null
        ? Number(raw.coverage_percentage_or_cap)
        : null,
    estimatedTotalCost:
      raw.estimatedTotalCost != null
        ? Number(raw.estimatedTotalCost)
        : raw.estimated_total_cost != null
        ? Number(raw.estimated_total_cost)
        : null,
    estimatedInsuranceShare:
      raw.estimatedInsuranceShare != null
        ? Number(raw.estimatedInsuranceShare)
        : raw.estimated_insurance_share != null
        ? Number(raw.estimated_insurance_share)
        : raw.estimated_insurer_contribution != null
        ? Number(raw.estimated_insurer_contribution)
        : null,
    estimatedPatientShare:
      raw.estimatedPatientShare != null
        ? Number(raw.estimatedPatientShare)
        : raw.estimated_patient_share != null
        ? Number(raw.estimated_patient_share)
        : raw.estimated_patient_responsibility != null
        ? Number(raw.estimated_patient_responsibility)
        : null,
    deductibleStatus:
      typeof raw.deductible_status === "string"
        ? raw.deductible_status
        : raw.deductible == null && raw.deductibleApplicable == null
        ? "not_determined"
        : "determined",
    deductibleApplicable:
      (raw.deductible_status === "not_determined" || (raw.deductible == null && raw.deductibleApplicable == null))
        ? null
        : raw.deductible != null
        ? Number(raw.deductible)
        : raw.deductibleApplicable != null
        ? Number(raw.deductibleApplicable)
        : null,
    isConditionalOnDeductible: Boolean(
      raw.is_conditional_on_deductible ??
      raw.isConditionalOnDeductible ??
      (raw.deductible_status === "not_determined" || (raw.deductible == null && raw.deductibleApplicable == null))
    ),
    policyCoverageCap:
      raw.policy_coverage_cap != null
        ? Number(raw.policy_coverage_cap)
        : raw.coverage_limit != null
        ? Number(raw.coverage_limit)
        : null,
    copayAmount:
      raw.copay != null ? Number(raw.copay) : raw.copayAmount != null ? Number(raw.copayAmount) : null,
    sublimitApplied:
      raw.coverage_limit != null
        ? Number(raw.coverage_limit)
        : raw.sublimitApplied != null
        ? Number(raw.sublimitApplied)
        : null,
    nonPayableConsumables: raw.nonPayableConsumables != null ? Number(raw.nonPayableConsumables) : null,
    waitingPeriodStatus: String(raw.waiting_periods || raw.waitingPeriodStatus || "Standard Period"),
    roomRuleApplied: String(raw.roomRuleApplied || "Standard Room Eligibility"),
    exclusionsList: Array.isArray(raw.exclusions)
      ? (raw.exclusions as string[])
      : Array.isArray(raw.exclusionsList)
      ? (raw.exclusionsList as string[])
      : [],
    evidenceList,
    evaluatedAt: String(raw.created_at || raw.evaluatedAt || new Date().toISOString()),
  };
}

export function normalizePolicy(raw: Record<string, unknown>): Policy {
  const rulesRaw = (raw.coverage_rules || raw.rules || []) as Record<string, unknown>[];
  const firstRule = rulesRaw.length > 0 ? rulesRaw[0] : null;
  const rawMeta = (raw.raw_metadata || raw.rawMetadata || {}) as Record<string, unknown>;
  const extractedMeta = (rawMeta.extracted_metadata || {}) as Record<string, unknown>;

  const id = String(raw.id ?? "1");
  const filename =
    typeof raw.filename === "string"
      ? raw.filename
      : typeof raw.documentFileName === "string"
      ? raw.documentFileName
      : "";
  const planName =
    (typeof raw.plan_name === "string" ? raw.plan_name : undefined) ||
    (typeof raw.planName === "string" ? raw.planName : undefined) ||
    (typeof extractedMeta.policy_name === "string" ? extractedMeta.policy_name : undefined) ||
    (filename ? filename.replace(/\.[^/.]+$/, "").replace(/_/g, " ") : undefined) ||
    "";
  const insurerName =
    (typeof raw.insurer_name === "string" ? raw.insurer_name : undefined) ||
    (typeof raw.insurerName === "string" ? raw.insurerName : undefined) ||
    (typeof extractedMeta.insurer_name === "string" ? extractedMeta.insurer_name : undefined) ||
    "";
  const policyNumber =
    (typeof raw.policy_number === "string" ? raw.policy_number : undefined) ||
    (typeof raw.policyNumber === "string" ? raw.policyNumber : undefined) ||
    (typeof extractedMeta.policy_id === "string" ? extractedMeta.policy_id : undefined) ||
    "";

  // Sum insured
  let sumInsured: number | null = null;
  if (firstRule && typeof firstRule.coverage_limit === "number") {
    sumInsured = firstRule.coverage_limit;
  } else if (typeof raw.sum_insured === "number") {
    sumInsured = raw.sum_insured;
  } else if (typeof raw.sumInsured === "number") {
    sumInsured = raw.sumInsured;
  } else if (rawMeta.out_of_pocket_max && typeof (rawMeta.out_of_pocket_max as Record<string, unknown>).individual_in_network === "number") {
    sumInsured = (rawMeta.out_of_pocket_max as Record<string, unknown>).individual_in_network as number;
  }

  // Deductible
  let deductible: number | null = null;
  if (firstRule && typeof firstRule.deductible === "number") {
    deductible = firstRule.deductible;
  } else if (typeof raw.deductible === "number") {
    deductible = raw.deductible;
  } else if (rawMeta.deductibles && typeof (rawMeta.deductibles as Record<string, unknown>).individual_in_network === "number") {
    deductible = (rawMeta.deductibles as Record<string, unknown>).individual_in_network as number;
  }

  // Copay percent
  let copayPercent: number | null = null;
  if (firstRule && typeof firstRule.copay_percentage === "number") {
    copayPercent = firstRule.copay_percentage;
  } else if (typeof raw.copay_percent === "number") {
    copayPercent = raw.copay_percent;
  } else if (typeof raw.copayPercent === "number") {
    copayPercent = raw.copayPercent;
  } else if (rawMeta.coinsurance && typeof (rawMeta.coinsurance as Record<string, unknown>).in_network_percentage === "number") {
    copayPercent = (rawMeta.coinsurance as Record<string, unknown>).in_network_percentage as number;
  }

  // Room rent limit
  const roomRentLimit =
    (firstRule && typeof firstRule.room_category === "string" ? firstRule.room_category : undefined) ||
    (typeof raw.room_rent_limit === "string" ? raw.room_rent_limit : undefined) ||
    (typeof raw.roomRentLimit === "string" ? raw.roomRentLimit : undefined) ||
    "Not Determined";

  const roomRentCondition =
    (typeof raw.roomRentCondition === "string" ? raw.roomRentCondition : undefined) ||
    (typeof raw.room_rent_condition === "string" ? raw.room_rent_condition : undefined) ||
    "Not Determined";

  const networkType =
    (typeof extractedMeta.network_name === "string" ? extractedMeta.network_name : undefined) ||
    (typeof raw.network_type === "string" ? raw.network_type : undefined) ||
    (typeof raw.networkType === "string" ? raw.networkType : undefined) ||
    "Not Determined";

  // Waiting period months
  let waitingPeriodMonths: number | null = null;
  if (firstRule && typeof firstRule.waiting_period === "string") {
    const m = firstRule.waiting_period.match(/(\d+)\s*(?:months?|m\b)/i);
    if (m) {
      waitingPeriodMonths = parseInt(m[1], 10);
    } else {
      const d = firstRule.waiting_period.match(/(\d+)\s*(?:years?|yrs?)/i);
      if (d) waitingPeriodMonths = parseInt(d[1], 10) * 12;
    }
  } else if (typeof raw.waitingPeriodMonths === "number") {
    waitingPeriodMonths = raw.waitingPeriodMonths;
  }

  const rules: CoverageRule[] = rulesRaw.map((r, idx) => ({
    id: String(r.id || `rule-${idx}`),
    category: String(r.category || "General"),
    ruleName: String(r.procedure_name || r.rule_name || r.source_reference || r.ruleName || "Coverage Clause"),
    description: String(r.description || r.waiting_period || r.conditions || r.network_condition || "Contractual Rule"),
    admissibilityStatus:
      r.coverage_status === "covered"
        ? "Covered"
        : r.coverage_status === "partially_covered"
        ? "Partial"
        : r.coverage_status === "not_covered"
        ? "Excluded"
        : "Not Determined",
    sublimit: r.coverage_limit_amount
      ? `Up to ₹${Number(r.coverage_limit_amount).toLocaleString()}`
      : r.coverage_limit
      ? `Up to ₹${Number(r.coverage_limit).toLocaleString()}`
      : undefined,
    copayPercent: typeof r.copay_percentage === "number" ? r.copay_percentage : undefined,
    clauseCitation: typeof r.source_reference === "string" ? r.source_reference : undefined,
  }));

  const derivedCategories = Array.from(new Set(rules.map((r) => r.category).filter(Boolean)));
  const categories = derivedCategories.length > 0
    ? derivedCategories.map((cat) => ({ name: cat, status: "Covered" }))
    : [];

  return {
    id,
    planName,
    insurerName,
    policyNumber,
    policyPeriod: "Annual (Active)",
    sumInsured,
    deductible,
    copayPercent,
    roomRentLimit,
    roomRentCondition,
    networkType,
    waitingPeriodMonths,
    categories,
    uploadedAt: String(raw.created_at || raw.uploadedAt || new Date().toISOString()),
    documentFileName: filename,
    documentFileSizeBytes: Number(rawMeta.size_bytes || raw.documentFileSizeBytes || 0),
    ocrConfidence: 0.96,
    rules,
  };
}

function normalizeDashboard(raw: Record<string, unknown>): DashboardOverview {
  const policiesAnalyzedCount = Number(
    raw.policiesAnalyzedCount ?? raw.policies_analyzed_count ?? raw.total_policies ?? 0
  );
  const coverageAnalysesCount = Number(
    raw.coverageAnalysesCount ?? raw.coverage_analyses_count ?? 0
  );
  const totalEstimatedPatientCosts = Number(
    raw.totalEstimatedPatientCosts ?? raw.total_estimated_patient_costs ?? 0
  );

  const rawRecent = (raw.recentAnalyses || raw.recent_analyses || []) as Record<string, unknown>[];
  const recentAnalyses: RecentAnalysisRecord[] = rawRecent.map((item) => ({
    id: String(item.id),
    policyId: item.policy_id != null ? String(item.policy_id) : (item.policyId != null ? String(item.policyId) : undefined),
    policy: String(item.policy ?? item.policy_name ?? `Policy #${item.policy_id || item.id}`),
    treatment: String(item.treatment ?? item.treatment_name ?? "General Treatment"),
    hospital: String(item.hospital ?? "Network Hospital"),
    estimatedCost:
      typeof (item.estimatedCost ?? item.estimated_cost) === "number"
        ? Number(item.estimatedCost ?? item.estimated_cost)
        : null,
    estimatedPatientShare:
      typeof (item.estimatedPatientShare ?? item.estimated_patient_share) === "number"
        ? Number(item.estimatedPatientShare ?? item.estimated_patient_share)
        : null,
    status:
      (item.status as CoverageStatus) ??
      (item.coverage_status === "likely_covered"
        ? "Likely Covered"
        : item.coverage_status === "partially_covered"
        ? "Partially Covered"
        : item.coverage_status === "not_covered"
        ? "Not Covered"
        : "Not Determined"),
    date: String(
      item.date ??
        (item.created_at
          ? new Date(String(item.created_at)).toISOString().split("T")[0]
          : new Date().toISOString().split("T")[0])
    ),
  }));

  let activePolicy: PolicySummary | null = null;
  const rawActive = (raw.activePolicy || raw.active_policy) as Record<string, unknown> | undefined;
  if (rawActive) {
    activePolicy = normalizePolicy(rawActive);
  }

  const rawCostChart = (raw.costComparisonChart || raw.cost_comparison_chart || []) as Record<string, unknown>[];
  const costComparisonChart = rawCostChart.map((c) => ({
    name: String(c.name ?? "Treatment"),
    total: Number(c.total || 0),
    insurer: Number(c.insurer || 0),
    patient: Number(c.patient || 0),
  }));

  return {
    policiesAnalyzedCount,
    coverageAnalysesCount,
    totalEstimatedPatientCosts,
    recentAnalyses,
    activePolicy,
    costComparisonChart,
  };
}

export function normalizeSimulationResult(raw: Record<string, unknown>): SimulationResult {
  const breakdown = (raw.calculation_breakdown as Record<string, unknown>) || {};
  const totalCost = Number(
    raw.totalCost ??
    raw.total_treatment_cost ??
    raw.hospital_quote ??
    raw.hospitalQuote ??
    breakdown.hospital_quote ??
    0
  );
  const insuranceShare = Number(
    raw.insuranceShare ??
    raw.estimated_insurance_share ??
    breakdown.insurer_payout ??
    0
  );
  const patientShare = Number(
    raw.patientShare ??
    raw.estimated_patient_share ??
    breakdown.patient_out_of_pocket ??
    0
  );
  const deductiblePaid = Number(
    raw.deductiblePaid ??
    raw.deductible ??
    breakdown.deductible_applied ??
    0
  );
  const copayPaid = Number(
    raw.copayPaid ??
    raw.copay ??
    breakdown.copay_applied ??
    0
  );
  const nonPayableTotal = Number(
    raw.nonPayableTotal ??
    raw.excluded_amount ??
    breakdown.non_payable_deduction ??
    0
  );
  const roomRentPenaltyAmount = Number(
    raw.roomRentPenaltyAmount ??
    breakdown.room_rent_penalty ??
    0
  );
  const effectivePercent = Number(
    raw.effectivePercent ??
    breakdown.effective_coverage_percentage ??
    (totalCost > 0 ? Math.round((insuranceShare / totalCost) * 100) : 0)
  );

  return {
    totalCost,
    contractedAllowance: Number(raw.contractedAllowance ?? breakdown.capped_eligible_amount ?? totalCost),
    insuranceShare,
    patientShare,
    deductiblePaid,
    copayPaid,
    nonPayableTotal,
    roomRentPenaltyAmount,
    effectivePercent,
    isLimitReached: Boolean(raw.isLimitReached ?? (Number(breakdown.excess_over_limit || 0) > 0)),
    currency: String(raw.currency ?? "INR"),
    calculatedAt: String(raw.calculatedAt ?? raw.created_at ?? new Date().toISOString()),
    rulesEngineVersion: String(raw.rulesEngineVersion ?? "Rules Engine v2.4 (Deterministic)"),
  };
}

export { parseApiError, createHttpError, CoverWiseApiError };
export type { ApiError };


