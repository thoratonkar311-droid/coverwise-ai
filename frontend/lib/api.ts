import {
  Policy,
  PolicySummary,
  AnalysisRequest,
  AnalysisResult,
  SimulationRequest,
  SimulationResult,
  DashboardOverview,
  RecentAnalysisRecord,
  ApiError,
} from "@/types";
import { parseApiError, createHttpError, CoverWiseApiError } from "./errors";
import {
  DEMO_FULL_POLICY,
  DEMO_POLICY,
  DEMO_COVERAGE_SCENARIOS,
  DEMO_DASHBOARD_OVERVIEW,
  DEMO_RECENT_ANALYSES,
  calculateMockSimulation,
} from "./mock-data";

/**
 * Base API URL configured via environment variable.
 * Does not hardcode localhost throughout the application.
 */
const API_BASE_URL = (process.env.NEXT_PUBLIC_API_URL || "").replace(/\/+$/, "");

/**
 * Flag determining whether to use mock data fallback or direct API calls.
 * Defaults to true if NEXT_PUBLIC_API_URL is not set or NEXT_PUBLIC_USE_MOCKS is not explicitly "false".
 */
const USE_MOCKS =
  process.env.NEXT_PUBLIC_USE_MOCKS === "true" ||
  process.env.NEXT_PUBLIC_USE_MOCKS !== "false" ||
  !API_BASE_URL;

const DEFAULT_TIMEOUT_MS = 15000;

/**
 * Helper to handle fetch with timeout and standard status code validation.
 */
async function fetchWithTimeout(
  url: string,
  options: RequestInit = {},
  timeoutMs: number = DEFAULT_TIMEOUT_MS
): Promise<Response> {
  const controller = new AbortController();
  const id = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetch(url, {
      ...options,
      signal: controller.signal,
      headers: {
        Accept: "application/json",
        ...(options.headers || {}),
      },
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
   * GET /api/health
   * Verifies API server and extraction engine availability.
   */
  async getHealth(): Promise<{ status: string; version: string; service: string }> {
    if (USE_MOCKS) {
      return {
        status: "ok",
        version: "2.4.0",
        service: "CoverWise Intelligence Service (Mock Active)",
      };
    }

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
    if (USE_MOCKS) {
      // Simulate network latency for realistic UX
      await new Promise((resolve) => setTimeout(resolve, 800));

      // Validate mock file format
      const validTypes = ["application/pdf", "image/png", "image/jpeg", "image/tiff"];
      if (file.type && !validTypes.includes(file.type)) {
        throw createHttpError(
          422,
          "Unsupported document format. Please upload a PDF, PNG, or JPEG file."
        );
      }

      return {
        ...DEMO_POLICY,
        planName: file.name.replace(/\.[^/.]+$/, "").replace(/_/g, " "),
      };
    }

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

      return await handleResponse<PolicySummary>(res);
    } catch (err) {
      throw parseApiError(err);
    }
  },

  /**
   * GET /api/policies/{id}
   * Fetches full extracted policy entity with rule clauses.
   */
  async getPolicyById(id: string): Promise<Policy> {
    if (USE_MOCKS) {
      await new Promise((resolve) => setTimeout(resolve, 300));
      if (id === "not-found" || id === "invalid") {
        throw createHttpError(404, `Policy document with ID '${id}' was not found.`);
      }
      return DEMO_FULL_POLICY;
    }

    try {
      const res = await fetchWithTimeout(`${API_BASE_URL}/api/policies/${encodeURIComponent(id)}`, {
        method: "GET",
      });
      return await handleResponse<Policy>(res);
    } catch (err) {
      throw parseApiError(err);
    }
  },

  /**
   * POST /api/analyses
   * Submits a treatment query against a policy to produce coverage intelligence.
   */
  async createAnalysis(request: AnalysisRequest): Promise<AnalysisResult> {
    if (USE_MOCKS) {
      await new Promise((resolve) => setTimeout(resolve, 600));

      const key = request.treatmentName.toLowerCase().includes("cataract")
        ? "cataract"
        : request.treatmentName.toLowerCase().includes("mri")
        ? "mri"
        : request.treatmentName.toLowerCase().includes("bariatric")
        ? "bariatric"
        : "knee";

      const matchedScenario = DEMO_COVERAGE_SCENARIOS[key];
      return {
        ...matchedScenario,
        policyId: request.policyId || DEMO_POLICY.id,
        treatmentName: request.treatmentName || matchedScenario.treatmentName,
        cptCode: request.cptCode || matchedScenario.cptCode,
        evaluatedAt: new Date().toISOString(),
      };
    }

    try {
      const res = await fetchWithTimeout(`${API_BASE_URL}/api/analyses`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(request),
      });
      return await handleResponse<AnalysisResult>(res);
    } catch (err) {
      throw parseApiError(err);
    }
  },

  /**
   * GET /api/analyses/{id}
   * Retrieves an existing coverage analysis by ID.
   */
  async getAnalysisById(id: string): Promise<AnalysisResult> {
    if (USE_MOCKS) {
      await new Promise((resolve) => setTimeout(resolve, 300));
      const scenario =
        Object.values(DEMO_COVERAGE_SCENARIOS).find((s) => s.id === id) ||
        DEMO_COVERAGE_SCENARIOS.knee;
      return scenario;
    }

    try {
      const res = await fetchWithTimeout(`${API_BASE_URL}/api/analyses/${encodeURIComponent(id)}`, {
        method: "GET",
      });
      return await handleResponse<AnalysisResult>(res);
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
    if (USE_MOCKS) {
      await new Promise((resolve) => setTimeout(resolve, 400));
      if (request.hospitalQuote < 0) {
        throw createHttpError(400, "Hospital quote amount cannot be negative.");
      }
      return calculateMockSimulation(request);
    }

    try {
      const res = await fetchWithTimeout(`${API_BASE_URL}/api/simulations`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(request),
      });
      return await handleResponse<SimulationResult>(res);
    } catch (err) {
      throw parseApiError(err);
    }
  },

  /**
   * GET /api/dashboard/overview
   * Fetches summary statistics and recent analyses for the intelligence dashboard.
   */
  async getDashboardOverview(): Promise<DashboardOverview> {
    if (USE_MOCKS) {
      await new Promise((resolve) => setTimeout(resolve, 350));
      return DEMO_DASHBOARD_OVERVIEW;
    }

    try {
      const res = await fetchWithTimeout(`${API_BASE_URL}/api/dashboard/overview`, {
        method: "GET",
      });
      return await handleResponse<DashboardOverview>(res);
    } catch (err) {
      throw parseApiError(err);
    }
  },

  /**
   * GET /api/analyses/recent
   * Fetches the user's recent policy analyses.
   */
  async getRecentAnalyses(): Promise<RecentAnalysisRecord[]> {
    if (USE_MOCKS) {
      await new Promise((resolve) => setTimeout(resolve, 200));
      return DEMO_RECENT_ANALYSES;
    }

    try {
      const res = await fetchWithTimeout(`${API_BASE_URL}/api/analyses/recent`, {
        method: "GET",
      });
      return await handleResponse<RecentAnalysisRecord[]>(res);
    } catch (err) {
      throw parseApiError(err);
    }
  },
};

export { parseApiError, createHttpError, CoverWiseApiError };
export type { ApiError };
