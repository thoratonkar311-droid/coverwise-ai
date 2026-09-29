"use client";

import React, { useState, useCallback, useEffect, Suspense } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Header } from "@/components/layout/Header";
import { Footer } from "@/components/layout/Footer";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { MetricCard } from "@/components/ui/MetricCard";
import { LoadingState } from "@/components/ui/LoadingState";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorState } from "@/components/ui/ErrorState";
import { EvidenceDrawer } from "@/components/coverage/EvidenceDrawer";
import { api, parseApiError } from "@/lib/api";
import {
  Policy,
  CoverageStatus,
  EvidenceReference,
  AnalysisResult,
  PolicySummary,
  ApiError,
} from "@/types";
import { formatCurrency, formatPercentage, displayValueOrNotDetermined } from "@/lib/utils";
import {
  CheckCircle2,
  AlertTriangle,
  XCircle,
  HelpCircle,
  FileSearch,
  ArrowRight,
  Shield,
  Coins,
  Calculator,
  Bed,
  Clock,
  SlidersHorizontal,
  Info,
} from "lucide-react";

type ScreenState = "success" | "loading" | "empty" | "error" | "not_determined";

function CoverageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const policyIdParam = searchParams.get("policyId");

  const [screenState, setScreenState] = useState<ScreenState>("loading");
  const [selectedTreatmentName, setSelectedTreatmentName] = useState<string>("Total Knee Replacement");
  const [customTreatmentInput, setCustomTreatmentInput] = useState<string>("");
  const [policy, setPolicy] = useState<Policy | PolicySummary | null>(null);
  const [analysis, setAnalysis] = useState<AnalysisResult | null>(null);
  const [apiError, setApiError] = useState<ApiError | null>(null);
  const [drawerOpen, setDrawerOpen] = useState<boolean>(false);
  const [activeEvidence, setActiveEvidence] = useState<EvidenceReference | null>(null);

  const getTargetPolicyId = useCallback((): string | null => {
    if (policyIdParam) return policyIdParam;
    if (typeof window !== "undefined") {
      const stored = localStorage.getItem("coverwise_active_policy_id");
      if (stored) return stored;
    }
    return null;
  }, [policyIdParam]);

  const loadCoverageData = useCallback((treatment: string) => {
    setSelectedTreatmentName(treatment);
    setScreenState("loading");
  }, []);

  useEffect(() => {
    let ignore = false;

    async function loadData() {
      let targetPolicyId = getTargetPolicyId();
      if (!targetPolicyId) {
        try {
          const overview = await api.getDashboardOverview();
          if (overview.activePolicy) {
            targetPolicyId = String(overview.activePolicy.id);
            if (typeof window !== "undefined") {
              localStorage.setItem("coverwise_active_policy_id", targetPolicyId);
            }
          }
        } catch {
          // ignore
        }
      }

      if (!targetPolicyId) {
        if (!ignore) {
          setScreenState("empty");
        }
        return;
      }

      try {
        const [fetchedPolicy, fetchedAnalysis] = await Promise.all([
          api.getPolicyById(targetPolicyId),
          api.createAnalysis({
            policyId: targetPolicyId,
            treatmentName: selectedTreatmentName,
          }),
        ]);

        if (!ignore) {
          setPolicy(fetchedPolicy);
          setAnalysis(fetchedAnalysis);
          setApiError(null);
          setScreenState("success");
        }
      } catch (err) {
        if (!ignore) {
          setApiError(parseApiError(err));
          setScreenState("error");
        }
      }
    }

    loadData();

    return () => {
      ignore = true;
    };
  }, [getTargetPolicyId, selectedTreatmentName]);

  const treatmentOptions = React.useMemo(() => {
    const list: { key: string; label: string; sub: string; tag: string }[] = [];
    if (policy && "rules" in policy && Array.isArray((policy as Policy).rules)) {
      for (const r of (policy as Policy).rules) {
        const name = r.ruleName || r.category;
        if (name && !list.some((it) => it.label.toLowerCase() === name.toLowerCase())) {
          list.push({
            key: String(r.id || name),
            label: name,
            sub: r.category || "Extracted Policy Rule",
            tag: r.admissibilityStatus || "Covered",
          });
        }
      }
    }
    if (list.length === 0) {
      list.push(
        { key: "tkr", label: "Total Knee Replacement", sub: "Orthopedic Surgery", tag: "Policy Rule" },
        { key: "cataract", label: "Cataract Surgery", sub: "Daycare Ophthalmology", tag: "Policy Rule" },
        { key: "angio", label: "Coronary Angioplasty", sub: "Cardiology", tag: "Policy Rule" },
        { key: "hernia", label: "Hernia Repair", sub: "General Surgery", tag: "Policy Rule" }
      );
    }
    return list;
  }, [policy]);

  const handleSelectTreatment = (treatment: string) => {
    loadCoverageData(treatment);
  };

  const handleOpenEvidence = (ev?: EvidenceReference) => {
    if (ev) {
      setActiveEvidence(ev);
    } else if (analysis?.evidenceList && analysis.evidenceList.length > 0) {
      setActiveEvidence(analysis.evidenceList[0]);
    }
    setDrawerOpen(true);
  };

  const renderStatusBadge = (status: CoverageStatus | undefined) => {
    switch (status) {
      case "Likely Covered":
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-[#ECFDF5] text-[#065F46] border border-emerald-300">
            <CheckCircle2 className="w-4 h-4 text-emerald-600" />
            Likely Covered
          </span>
        );
      case "Partially Covered":
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-[#EFF6FF] text-[#1E40AF] border border-blue-300">
            <HelpCircle className="w-4 h-4 text-blue-600" />
            Partially Covered
          </span>
        );
      case "Not Covered":
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-[#FEF2F2] text-[#991B1B] border border-rose-300">
            <XCircle className="w-4 h-4 text-rose-600" />
            Not Covered
          </span>
        );
      case "Not Determined":
      default:
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-slate-100 text-slate-800 border border-slate-300">
            <HelpCircle className="w-4 h-4 text-slate-500" />
            Not Determined
          </span>
        );
    }
  };

  // Construct a fallback "Not Determined" analysis representation when requested
  const currentAnalysis: AnalysisResult | null =
    screenState === "not_determined"
      ? {
          id: "analysis-undetermined",
          policyId: "pol-unknown",
          treatmentName: "Experimental Cellular Therapy",
          treatmentCategory: "Unclassified Procedure",
          cptCode: "CPT 99999",
          coverageStatus: "Not Determined",
          coveragePercentage: null,
          estimatedTotalCost: null,
          estimatedInsuranceShare: null,
          estimatedPatientShare: null,
          deductibleApplicable: null,
          copayAmount: null,
          sublimitApplied: null,
          nonPayableConsumables: null,
          waitingPeriodStatus: "Not Determined (Clause verification pending)",
          roomRuleApplied: "Not Determined",
          exclusionsList: ["Admissibility pending medical necessity documentation"],
          evidenceList: [],
          evaluatedAt: new Date().toISOString(),
        }
      : analysis;

  return (
    <div className="min-h-screen flex flex-col bg-[#F8F9FF] text-[#0A1D2E] antialiased">
      <Header />

      <main className="flex-1 py-10 sm:py-16">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 space-y-8">
          {/* Top Bar: Breadcrumb & State Controls */}
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div className="flex items-center gap-2 text-xs text-slate-500">
              <Link href="/" className="hover:text-[#0052D1]">
                Home
              </Link>
              <span>/</span>
              <Link href="/analyze" className="hover:text-[#0052D1]">
                Analyze
              </Link>
              <span>/</span>
              <span className="font-semibold text-slate-800">Coverage Intelligence</span>
            </div>

            {/* Interactive State Demo Switcher */}
            <div className="flex flex-wrap items-center gap-2 p-1 rounded-xl bg-white border border-slate-200 shadow-xs">
              <span className="text-[11px] font-semibold text-slate-400 px-2 uppercase">
                API State:
              </span>
              {(["success", "loading", "empty", "error", "not_determined"] as ScreenState[]).map((st) => (
                <button
                  key={st}
                  onClick={() => {
                    if (st === "success") {
                      loadCoverageData(selectedTreatmentName);
                    } else if (st === "error") {
                      setApiError({
                        statusCode: 500,
                        code: "COVERAGE_EVALUATION_FAIL",
                        message: "The coverage reasoning pipeline failed to compute benefit limits.",
                        details: "Timeout occurred while connecting to underwriting rules service.",
                        timestamp: new Date().toISOString(),
                      });
                      setScreenState("error");
                    } else {
                      setScreenState(st);
                    }
                  }}
                  className={`text-xs px-2.5 py-1 rounded-lg capitalize font-medium transition-colors cursor-pointer ${
                    screenState === st
                      ? "bg-[#0052D1] text-white"
                      : "text-slate-600 hover:bg-slate-100"
                  }`}
                >
                  {st.replace("_", " ")}
                </button>
              ))}
            </div>
          </div>

          {/* STATE: Loading */}
          {screenState === "loading" && (
            <div className="space-y-6">
              <div className="p-8 rounded-2xl bg-white border border-slate-200 flex flex-col items-center justify-center gap-4 py-16">
                <LoadingState
                  variant="spinner"
                  size="lg"
                  message="Connecting to Coverage Intelligence Engine..."
                />
                <p className="text-xs text-slate-400">
                  Retrieving policy schedule clauses and computing deterministic co-pay caps.
                </p>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                <LoadingState variant="skeleton" lines={2} className="p-6 bg-white rounded-2xl border" />
                <LoadingState variant="skeleton" lines={2} className="p-6 bg-white rounded-2xl border" />
                <LoadingState variant="skeleton" lines={2} className="p-6 bg-white rounded-2xl border" />
                <LoadingState variant="skeleton" lines={2} className="p-6 bg-white rounded-2xl border" />
              </div>
            </div>
          )}

          {/* STATE: Error */}
          {screenState === "error" && (
            <Card className="border-red-200 bg-white p-8">
              <ErrorState
                title="Failed to Load Coverage Intelligence"
                message={apiError?.message || "An unexpected error occurred while communicating with the analysis service."}
                details={
                  apiError?.details
                    ? typeof apiError.details === "string"
                      ? apiError.details
                      : JSON.stringify(apiError.details)
                    : `Status Code: ${apiError?.statusCode || 500} • Request: ${apiError?.code || "CW_COV_EVAL_FAIL"}`
                }
                onRetry={() => loadCoverageData(selectedTreatmentName)}
                retryLabel="Retry Analysis"
              />
              <div className="mt-6 pt-6 border-t border-slate-100 flex justify-center gap-3">
                <Link href="/analyze">
                  <Button variant="outline" size="sm">
                    Upload New Policy
                  </Button>
                </Link>
                <Button variant="primary" size="sm" onClick={() => loadCoverageData("Total Knee Replacement")}>
                  Analyze Knee Replacement
                </Button>
              </div>
            </Card>
          )}

          {/* STATE: Empty */}
          {screenState === "empty" && (
            <Card className="border-slate-200 bg-white p-12 text-center">
              <EmptyState
                title="No Policy Analysis Found"
                description="Upload an active policy schedule to evaluate coverage and patient responsibility."
                actionLabel="Upload Policy Document"
                onAction={() => router.push("/analyze")}
              />
            </Card>
          )}

          {/* STATE: Success or Not Determined */}
          {(screenState === "success" || screenState === "not_determined") && currentAnalysis && (
            <>
              {/* Policy Summary Header Card */}
              <Card className="border-slate-200 shadow-sm bg-white overflow-hidden">
                <div className="p-6 bg-gradient-to-r from-[#EEF4FF] via-white to-[#E6F7F5] border-b border-slate-100 flex flex-col md:flex-row md:items-center justify-between gap-4">
                  <div className="flex items-start sm:items-center gap-3.5">
                    <div className="w-12 h-12 rounded-2xl bg-[#0052D1] text-white flex items-center justify-center font-bold shadow-md shadow-blue-600/10">
                      <Shield className="w-6 h-6" />
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <h2 className="text-base sm:text-lg font-bold text-[#0A1D2E]">
                          {displayValueOrNotDetermined(policy?.planName)}
                        </h2>
                        <Badge variant="teal" size="xs">
                          Active
                        </Badge>
                      </div>
                      <p className="text-xs text-slate-500">
                        {displayValueOrNotDetermined(policy?.insurerName)} • Policy Number:{" "}
                        <span className="font-mono font-medium text-slate-700">
                          {displayValueOrNotDetermined(policy?.policyNumber)}
                        </span>
                      </p>
                    </div>
                  </div>

                  <div className="flex flex-wrap items-center gap-3 text-xs">
                    <div className="p-2.5 rounded-xl bg-white border border-slate-200 text-slate-700">
                      <span className="text-[10px] text-slate-400 block uppercase font-semibold">
                        Sum Insured
                      </span>
                      <span className="font-mono font-bold text-slate-900">
                        {formatCurrency(policy?.sumInsured)}
                      </span>
                    </div>
                    <div className="p-2.5 rounded-xl bg-white border border-slate-200 text-slate-700">
                      <span className="text-[10px] text-slate-400 block uppercase font-semibold">
                        Network
                      </span>
                      <span className="font-semibold text-[#006B5F]">
                        {displayValueOrNotDetermined(policy?.networkType)}
                      </span>
                    </div>
                  </div>
                </div>
              </Card>

              {/* Treatment Selection Bar */}
              <div className="space-y-3">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                  <div>
                    <span className="text-xs font-bold uppercase tracking-wider text-slate-500 block">
                      Select or Search Procedure:
                    </span>
                    <span className="text-xs text-slate-400">
                      Evaluated directly against active policy contractual rules
                    </span>
                  </div>
                  <form
                    onSubmit={(e) => {
                      e.preventDefault();
                      if (customTreatmentInput.trim()) {
                        handleSelectTreatment(customTreatmentInput.trim());
                      }
                    }}
                    className="flex items-center gap-2"
                  >
                    <input
                      type="text"
                      placeholder="Search any procedure..."
                      value={customTreatmentInput}
                      onChange={(e) => setCustomTreatmentInput(e.target.value)}
                      className="text-xs px-3 py-1.5 rounded-lg border border-slate-200 bg-white focus:outline-none focus:ring-1 focus:ring-[#0052D1] w-48 sm:w-64"
                    />
                    <Button variant="primary" size="sm" type="submit">
                      Analyze
                    </Button>
                  </form>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
                  {treatmentOptions.map((item) => {
                    const isSelected = selectedTreatmentName.toLowerCase() === item.label.toLowerCase() && screenState !== "not_determined";
                    return (
                      <button
                        key={item.key}
                        onClick={() => handleSelectTreatment(item.label)}
                        className={`p-3.5 rounded-xl border text-left transition-all cursor-pointer flex flex-col justify-between gap-2 ${
                          isSelected
                            ? "bg-[#0052D1] text-white border-[#0052D1] shadow-md shadow-blue-600/15"
                            : "bg-white text-slate-700 border-slate-200 hover:border-blue-200 hover:bg-[#EEF4FF]"
                        }`}
                      >
                        <div>
                          <p className="text-sm font-bold truncate">{item.label}</p>
                          <p className={`text-[11px] ${isSelected ? "text-blue-100" : "text-slate-400"}`}>
                            {item.sub}
                          </p>
                        </div>
                        <span
                          className={`text-[10px] font-semibold uppercase px-2 py-0.5 rounded-md w-fit ${
                            isSelected
                              ? "bg-white/20 text-white"
                              : item.tag === "Not Covered" || item.tag === "Excluded"
                              ? "bg-red-50 text-red-700 border border-red-200"
                              : item.tag === "Likely Covered" || item.tag === "Covered"
                              ? "bg-emerald-50 text-emerald-700 border border-emerald-200"
                              : item.tag === "Partially Covered" || item.tag === "Partial"
                              ? "bg-blue-50 text-blue-700 border border-blue-200"
                              : "bg-slate-100 text-slate-700 border border-slate-200"
                          }`}
                        >
                          {item.tag}
                        </span>
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* Active Treatment Overview Banner */}
              <div className="p-6 rounded-2xl bg-white border border-slate-200 shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div>
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-xs font-mono text-slate-500">
                      {displayValueOrNotDetermined(currentAnalysis.cptCode)}
                    </span>
                    <span className="text-slate-300">•</span>
                    <span className="text-xs font-semibold text-slate-600">
                      {displayValueOrNotDetermined(currentAnalysis.treatmentCategory)}
                    </span>
                  </div>
                  <h1 className="text-2xl font-extrabold text-[#0A1D2E] tracking-tight">
                    {displayValueOrNotDetermined(currentAnalysis.treatmentName)}
                  </h1>
                </div>

                <div className="flex flex-wrap items-center gap-3">
                  {renderStatusBadge(currentAnalysis.coverageStatus)}
                  <Button
                    variant="outline"
                    size="sm"
                    leftIcon={<FileSearch className="w-4 h-4 text-[#0052D1]" />}
                    onClick={() => handleOpenEvidence()}
                  >
                    View Evidence ({currentAnalysis.evidenceList?.length || 0})
                  </Button>
                </div>
              </div>

              {/* Top Numeric Metric Cards Row */}
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                <MetricCard
                  label="Coverage Percentage"
                  value={formatPercentage(currentAnalysis.coveragePercentage)}
                  sourceTier="deterministic_calc"
                  sourceLabel="Deterministic Rule"
                  subtext="Admissible allowance share"
                  icon={<Calculator className="w-5 h-5 text-[#006B5F]" />}
                />

                <MetricCard
                  label="Estimated Treatment"
                  value={formatCurrency(currentAnalysis.estimatedTotalCost)}
                  sourceTier="policy_source"
                  sourceLabel="Hospital Tariff"
                  subtext="Estimated total procedure cost"
                  icon={<Shield className="w-5 h-5" />}
                />

                <MetricCard
                  label="Estimated Insurer Share"
                  value={formatCurrency(currentAnalysis.estimatedInsuranceShare)}
                  sourceTier="deterministic_calc"
                  sourceLabel="Covered Benefit"
                  subtext="Direct cashless authorization"
                  icon={<CheckCircle2 className="w-5 h-5 text-emerald-600" />}
                />

                <MetricCard
                  label="Estimated Patient Share"
                  value={formatCurrency(currentAnalysis.estimatedPatientShare)}
                  sourceTier="estimated_result"
                  sourceLabel={currentAnalysis.deductibleStatus === "not_determined" ? "Conditional Estimate" : "Patient Estimate"}
                  subtext={
                    currentAnalysis.deductibleStatus === "not_determined"
                      ? "Conditional on ₹0 deductible"
                      : "Deductible + Copay + Consumables"
                  }
                  highlight
                  icon={<Coins className="w-5 h-5 text-[#0052D1]" />}
                />
              </div>

              {/* Detailed Policy Conditions Grid */}
              <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
                {/* Left 7 Columns: Breakdown and Rules */}
                <div className="lg:col-span-7 space-y-6">
                  <Card className="border-slate-200 shadow-sm bg-white">
                    <CardHeader>
                      <CardTitle>Applicable Policy Parameters & Caps</CardTitle>
                      <CardDescription>
                        Exact sub-limits, deductibles, and room-rent conditions applied to this procedure.
                      </CardDescription>
                    </CardHeader>

                    <CardContent className="space-y-4">
                      {currentAnalysis.deductibleStatus === "not_determined" && (
                        <div className="p-3 rounded-xl bg-amber-50/70 border border-amber-200 text-xs text-amber-900 flex items-start gap-2.5">
                          <Info className="w-4 h-4 text-amber-700 shrink-0 mt-0.5" />
                          <span>
                            <strong>Policy Deductible: Not Determined.</strong> The policy terms do not establish an individual deductible. Financial calculations are conditional on ₹0 deductible being applied upon claim adjudication.
                          </span>
                        </div>
                      )}

                      <div className="divide-y divide-slate-100 text-xs">
                        <div className="py-3 flex items-center justify-between">
                          <span className="text-slate-600 font-medium">Individual Deductible:</span>
                          <span className={`font-mono font-semibold ${
                            currentAnalysis.deductibleStatus === "not_determined" || currentAnalysis.deductibleApplicable == null
                              ? "text-slate-500 italic text-[11px]"
                              : "text-slate-900"
                          }`}>
                            {currentAnalysis.deductibleStatus === "not_determined" || currentAnalysis.deductibleApplicable == null
                              ? "Not Determined"
                              : formatCurrency(currentAnalysis.deductibleApplicable)}
                          </span>
                        </div>

                        <div className="py-3 flex items-center justify-between">
                          <span className="text-slate-600 font-medium">Mandatory Co-Payment Amount:</span>
                          <span className="font-mono text-slate-900 font-semibold">
                            {formatCurrency(currentAnalysis.copayAmount)}
                          </span>
                        </div>

                        <div className="py-3 flex items-center justify-between">
                          <span className="text-slate-600 font-medium">Procedure Sub-Limit / Cap:</span>
                          <span className="font-mono text-slate-900 font-semibold">
                            {currentAnalysis.sublimitApplied
                              ? formatCurrency(currentAnalysis.sublimitApplied)
                              : "Not Capped (Sum Insured)"}
                          </span>
                        </div>

                        <div className="py-3 flex items-center justify-between">
                          <span className="text-slate-600 font-medium">Non-Payable Consumables Estimate:</span>
                          <span className="font-mono text-amber-800 font-semibold">
                            {formatCurrency(currentAnalysis.nonPayableConsumables)}
                          </span>
                        </div>
                      </div>

                      {/* Room Category & Waiting Period Highlights */}
                      <div className="pt-2 grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
                        <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200/80 flex flex-col gap-1">
                          <div className="flex items-center gap-1.5 text-slate-700 font-semibold">
                            <Bed className="w-4 h-4 text-[#0052D1]" />
                            <span>Room Category Rule</span>
                          </div>
                          <p className="text-slate-600 text-[11px] leading-relaxed">
                            {displayValueOrNotDetermined(currentAnalysis.roomRuleApplied)}
                          </p>
                        </div>

                        <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200/80 flex flex-col gap-1">
                          <div className="flex items-center gap-1.5 text-slate-700 font-semibold">
                            <Clock className="w-4 h-4 text-emerald-600" />
                            <span>Waiting Period Status</span>
                          </div>
                          <p className="text-slate-600 text-[11px] leading-relaxed">
                            {displayValueOrNotDetermined(currentAnalysis.waitingPeriodStatus)}
                          </p>
                        </div>
                      </div>

                      {/* Exclusions Box */}
                      <div className="p-4 rounded-xl bg-rose-50/50 border border-rose-200/80 space-y-2">
                        <span className="text-[11px] font-bold uppercase tracking-wider text-rose-800 flex items-center gap-1.5">
                          <AlertTriangle className="w-3.5 h-3.5 text-rose-600" />
                          Specific Non-Covered Items / Exclusions
                        </span>
                        <ul className="space-y-1.5 text-xs text-rose-950">
                          {currentAnalysis.exclusionsList?.map((exc, i) => (
                            <li key={i} className="flex items-start gap-2">
                              <span className="text-rose-500 font-bold">•</span>
                              <span>{exc}</span>
                            </li>
                          ))}
                        </ul>
                      </div>
                    </CardContent>
                  </Card>
                </div>

                {/* Right 5 Columns: "Why this result?" Evidence Section */}
                <div className="lg:col-span-5 space-y-4">
                  <Card className="border-l-4 border-l-[#0052D1] shadow-sm bg-white">
                    <CardHeader>
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-bold uppercase tracking-wider text-[#0052D1]">
                          Reasoning & Evidence
                        </span>
                        <StatusBadge variant="ai_interpretation" size="xs" label="Audit Trace" />
                      </div>
                      <CardTitle className="text-base mt-1">Why this result?</CardTitle>
                      <CardDescription>
                        Understanding how policy clauses led to the {currentAnalysis.coverageStatus} determination.
                      </CardDescription>
                    </CardHeader>

                    <CardContent className="space-y-4 pt-0">
                      {currentAnalysis.evidenceList && currentAnalysis.evidenceList.length > 0 ? (
                        <div className="space-y-3">
                          <div className="p-3.5 rounded-xl bg-[#EEF4FF]/50 border border-blue-100 text-xs text-slate-800 leading-relaxed italic">
                            “{currentAnalysis.evidenceList[0].sourceText}”
                          </div>

                          <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200/80 space-y-2 text-xs">
                            <div className="flex justify-between">
                              <span className="text-slate-500">Cited Clause:</span>
                              <span className="font-semibold text-slate-800 truncate max-w-[200px]">
                                {currentAnalysis.evidenceList[0].clauseReference}
                              </span>
                            </div>
                            <div className="flex justify-between">
                              <span className="text-slate-500">Confidence Score:</span>
                              <span className="font-mono font-bold text-emerald-700">
                                {currentAnalysis.evidenceList[0].confidence}%
                              </span>
                            </div>
                            <div className="pt-2 border-t border-slate-200 text-slate-600">
                              <span className="font-semibold text-slate-800">Interpretation: </span>
                              {currentAnalysis.evidenceList[0].aiInterpretation}
                            </div>
                          </div>

                          <Button
                            variant="primary"
                            size="sm"
                            onClick={() => handleOpenEvidence(currentAnalysis.evidenceList[0])}
                            leftIcon={<FileSearch className="w-4 h-4" />}
                            className="w-full justify-center font-semibold"
                          >
                            Open Full Evidence Drawer
                          </Button>
                        </div>
                      ) : (
                        <div className="p-6 rounded-xl bg-slate-50 border border-dashed border-slate-200 text-center space-y-2">
                          <HelpCircle className="w-6 h-6 text-slate-400 mx-auto" />
                          <p className="text-xs font-semibold text-slate-700">No Direct Policy Citation Found</p>
                          <p className="text-[11px] text-slate-500">
                            The requested treatment could not be matched directly to named coverage clauses or schedules.
                          </p>
                        </div>
                      )}
                    </CardContent>
                  </Card>

                  {/* Cost Simulator Callout Banner */}
                  <div className="p-5 rounded-2xl bg-gradient-to-br from-[#0A1D2E] to-[#152e46] text-white space-y-3">
                    <div className="flex items-center gap-2 text-xs font-semibold text-[#71F8E4]">
                      <SlidersHorizontal className="w-4 h-4" />
                      <span>Interactive Cost Simulator</span>
                    </div>
                    <h4 className="text-sm font-bold text-white">
                      Want to model different hospital tariffs or room tiers?
                    </h4>
                    <p className="text-xs text-slate-300 leading-relaxed">
                      Test custom billing quotes, deluxe suite room-rent penalties, and consumable
                      variations in the Cost Simulator.
                    </p>
                    <Link href={policy?.id ? `/simulator?policyId=${policy.id}` : "/simulator"} className="block pt-1">
                      <Button
                        variant="teal"
                        size="sm"
                        className="w-full justify-center font-semibold"
                        rightIcon={<ArrowRight className="w-3.5 h-3.5" />}
                      >
                        Simulate Hospital Bills
                      </Button>
                    </Link>
                  </div>
                </div>
              </div>
            </>
          )}
        </div>
      </main>

      <Footer />

      {/* Reusable Evidence Drawer */}
      <EvidenceDrawer
        isOpen={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        evidence={activeEvidence}
        allEvidence={currentAnalysis?.evidenceList || []}
        onSelectEvidence={(ev) => setActiveEvidence(ev)}
      />
    </div>
  );
}

export default function CoveragePage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen flex items-center justify-center bg-[#F8F9FF]">
          <div className="w-8 h-8 border-3 border-[#0052D1] border-t-transparent rounded-full animate-spin" />
        </div>
      }
    >
      <CoverageContent />
    </Suspense>
  );
}

