"use client";

import React, { useState, useEffect, useCallback, useRef, Suspense } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Header } from "@/components/layout/Header";
import { Footer } from "@/components/layout/Footer";
import { SectionHeader } from "@/components/ui/SectionHeader";
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { MetricCard } from "@/components/ui/MetricCard";
import { LoadingState } from "@/components/ui/LoadingState";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorState } from "@/components/ui/ErrorState";
import { api, parseApiError } from "@/lib/api";
import { SimulationRequest, SimulationResult, PolicySummary, ApiError } from "@/types";
import { formatCurrency } from "@/lib/utils";
import {
  PieChart,
  Pie,
  Cell,
  ResponsiveContainer,
  Tooltip as RechartsTooltip,
} from "recharts";
import {
  RotateCcw,
  Info,
} from "lucide-react";

type ScreenState = "success" | "loading" | "empty" | "error" | "not_determined";

interface PresetTreatment {
  name: string;
  quote: number;
  room: string;
  deductible: number;
  copay: number;
  limit: number;
  consumables: number;
}

const PRESETS: Record<string, PresetTreatment> = {
  knee: {
    name: "Total Knee Replacement",
    quote: 250000,
    room: "Single Private Room",
    deductible: 0,
    copay: 0,
    limit: 1000000,
    consumables: 0,
  },
  cataract: {
    name: "Cataract Surgery (Monofocal)",
    quote: 45000,
    room: "Daycare (No Room Charge)",
    deductible: 0,
    copay: 0,
    limit: 1000000,
    consumables: 3375,
  },
  mri: {
    name: "MRI Brain with Contrast",
    quote: 22000,
    room: "Outpatient Center",
    deductible: 0,
    copay: 0,
    limit: 1000000,
    consumables: 3000,
  },
  angioplasty: {
    name: "Coronary Angioplasty (Single Stent)",
    quote: 210000,
    room: "Single Private Room",
    deductible: 0,
    copay: 0,
    limit: 1000000,
    consumables: 14000,
  },
};

function SimulatorContent() {
  const searchParams = useSearchParams();
  const policyIdParam = searchParams.get("policyId");

  const [activePolicyId, setActivePolicyId] = useState<string | null>(() => {
    if (policyIdParam) return policyIdParam;
    if (typeof window !== "undefined") {
      return localStorage.getItem("coverwise_active_policy_id");
    }
    return null;
  });

  const [activePolicy, setActivePolicy] = useState<PolicySummary | null>(null);
  const [screenState, setScreenState] = useState<ScreenState>("loading");
  const [selectedPreset, setSelectedPreset] = useState<string>("knee");
  const [treatmentName, setTreatmentName] = useState<string>("Total Knee Replacement");
  const [hospitalQuote, setHospitalQuote] = useState<number>(250000);
  const [roomCategory, setRoomCategory] = useState<string>("Single Private Room");
  const [deductible, setDeductible] = useState<number>(0);
  const [copayPercent, setCopayPercent] = useState<number>(0);
  const [coverageLimit, setCoverageLimit] = useState<number>(1000000);
  const [consumables, setConsumables] = useState<number>(0);
  const [calculation, setCalculation] = useState<SimulationResult | null>(null);
  const [isCalculating, setIsCalculating] = useState<boolean>(false);
  const [apiError, setApiError] = useState<ApiError | null>(null);
  const debounceRef = useRef<NodeJS.Timeout | null>(null);

  // Calls API client to perform simulation calculation (frontend is not calculation source of truth)
  const runSimulation = useCallback(async (requestPayload: SimulationRequest) => {
    setIsCalculating(true);
    try {
      const result = await api.createSimulation(requestPayload);
      setCalculation(result);
      setApiError(null);
      setScreenState("success");
    } catch (err) {
      setApiError(parseApiError(err));
      setScreenState("error");
    } finally {
      setIsCalculating(false);
    }
  }, []);

  // Initialize and resolve active policy
  useEffect(() => {
    let isMounted = true;
    async function initPolicy() {
      let targetId = activePolicyId;
      if (!targetId) {
        try {
          const overview = await api.getDashboardOverview();
          if (overview.activePolicy) {
            targetId = String(overview.activePolicy.id);
            if (typeof window !== "undefined") {
              localStorage.setItem("coverwise_active_policy_id", targetId);
            }
            if (isMounted) setActivePolicyId(targetId);
          }
        } catch {
          // ignore
        }
      }

      if (!targetId) {
        if (isMounted) setScreenState("empty");
        return;
      }

      try {
        const p = await api.getPolicyById(targetId);
        if (!isMounted || !p) return;
        setActivePolicy(p);
        const initDeductible = p.deductible ?? 0;
        const initCopay = p.copayPercent ?? 0;
        const initLimit = p.sumInsured ?? 1000000;
        setDeductible(initDeductible);
        setCopayPercent(initCopay);
        setCoverageLimit(initLimit);

        // Run initial simulation calculation with policy rules
        runSimulation({
          policyId: targetId,
          treatment: "Total Knee Replacement",
          hospitalQuote: 250000,
          roomCategory: "Single Private Room",
          deductible: initDeductible,
          copayPercent: initCopay,
          coverageLimit: initLimit,
          consumablesEstimate: 0,
        });
      } catch {
        if (isMounted) setScreenState("empty");
      }
    }

    initPolicy();
    return () => {
      isMounted = false;
    };
  }, [activePolicyId, runSimulation]);

  // Debounced effect whenever inputs change
  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);

    debounceRef.current = setTimeout(() => {
      const payload: SimulationRequest = {
        policyId: activePolicyId || undefined,
        treatment: treatmentName,
        hospitalQuote,
        roomCategory,
        deductible,
        copayPercent,
        coverageLimit,
        consumablesEstimate: consumables,
      };
      runSimulation(payload);
    }, 150);

    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [
    activePolicyId,
    treatmentName,
    hospitalQuote,
    roomCategory,
    deductible,
    copayPercent,
    coverageLimit,
    consumables,
    runSimulation,
  ]);

  // Apply preset values
  const handleSelectPreset = (key: string) => {
    setSelectedPreset(key);
    const p = PRESETS[key];
    if (p) {
      setTreatmentName(p.name);
      setHospitalQuote(p.quote);
      setRoomCategory(p.room);
      setConsumables(p.consumables);
      if (activePolicy) {
        setDeductible(activePolicy.deductible ?? 0);
        setCopayPercent(activePolicy.copayPercent ?? 0);
        setCoverageLimit(activePolicy.sumInsured ?? 1000000);
      } else {
        setDeductible(p.deductible);
        setCopayPercent(p.copay);
        setCoverageLimit(p.limit);
      }
    }
  };

  const chartData = calculation
    ? [
        { name: "Insurance Share", value: calculation.insuranceShare, color: "#006B5F" },
        { name: "Patient Co-Pay", value: calculation.copayPaid, color: "#0052D1" },
        { name: "Deductible", value: calculation.deductiblePaid, color: "#D97706" },
        { name: "Non-Payables", value: calculation.nonPayableTotal, color: "#BA1A1A" },
      ].filter((d) => d.value > 0)
    : [];

  return (
    <div className="min-h-screen flex flex-col bg-[#F8F9FF] text-[#0A1D2E] antialiased">
      <Header />

      <main className="flex-1 py-10 sm:py-16">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 space-y-10">
          {/* Top Bar: Breadcrumb & State Controls */}
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div className="flex items-center gap-2 text-xs text-slate-500">
              <Link href="/" className="hover:text-[#0052D1]">
                Home
              </Link>
              <span>/</span>
              <Link href="/coverage" className="hover:text-[#0052D1]">
                Coverage Intelligence
              </Link>
              <span>/</span>
              <span className="font-semibold text-slate-800">Treatment Cost Simulator</span>
            </div>

            {/* State Toggles for Audit & Review */}
            <div className="flex flex-wrap items-center gap-2 p-1 rounded-xl bg-white border border-slate-200 shadow-xs">
              <span className="text-[11px] font-semibold text-slate-400 px-2 uppercase">
                Simulator State:
              </span>
              {(["success", "loading", "empty", "error", "not_determined"] as ScreenState[]).map((st) => (
                <button
                  key={st}
                  onClick={() => {
                    if (st === "error") {
                      setApiError({
                        statusCode: 400,
                        code: "INVALID_SIMULATION_PARAMETERS",
                        message: "The rules engine rejected the calculation parameters due to contradictory clauses.",
                        details: "Hospital quote exceeded statutory single-event limits for current coverage tier.",
                        timestamp: new Date().toISOString(),
                      });
                      setScreenState("error");
                    } else if (st === "empty") {
                      setCalculation(null);
                      setScreenState("empty");
                    } else {
                      setScreenState(st);
                      if (st === "success" && !calculation) {
                        handleSelectPreset("knee");
                      }
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

          <SectionHeader
            badge="Treatment Cost Simulator"
            badgeVariant="teal"
            title="Model Your Out-of-Pocket Hospital Costs"
            description="Adjust billed estimates, room categories, and copayment rates to see how backend policy rules compute patient responsibility."
          />

          {/* Quick Preset Selector */}
          <div className="p-4 rounded-2xl bg-white border border-slate-200 shadow-xs flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-500">
              Quick Scenario Presets:
            </span>
            <div className="flex flex-wrap gap-2">
              {[
                { key: "knee", label: "Knee Replacement (₹2.5L)" },
                { key: "cataract", label: "Cataract (₹45k)" },
                { key: "mri", label: "Brain MRI (₹22k)" },
                { key: "angioplasty", label: "Angioplasty (₹2.1L)" },
              ].map((p) => (
                <button
                  key={p.key}
                  onClick={() => handleSelectPreset(p.key)}
                  className={`text-xs px-3 py-1.5 rounded-lg border font-medium transition-all cursor-pointer ${
                    selectedPreset === p.key
                      ? "bg-[#0052D1] text-white border-[#0052D1]"
                      : "bg-slate-50 text-slate-700 border-slate-200 hover:bg-slate-100"
                  }`}
                >
                  {p.label}
                </button>
              ))}
            </div>
          </div>

          {/* STATE: Loading */}
          {screenState === "loading" && (
            <Card className="border-slate-200 bg-white p-12 text-center">
              <LoadingState
                variant="spinner"
                size="lg"
                message="Evaluating Financial Calculation Rules..."
              />
              <p className="text-xs text-slate-400 mt-2">
                Running deductible adjudication and proportional room penalty algorithms.
              </p>
            </Card>
          )}

          {/* STATE: Error */}
          {screenState === "error" && (
            <Card className="border-red-200 bg-white p-8">
              <ErrorState
                title="Simulation Engine Error"
                message={apiError?.message || "The rules engine could not compute cost allocation for these parameters."}
                details={
                  apiError?.details
                    ? typeof apiError.details === "string"
                      ? apiError.details
                      : JSON.stringify(apiError.details)
                    : `Error Code: ${apiError?.code || "CALC_FAIL"} • Status: ${apiError?.statusCode || 500}`
                }
                onRetry={() => handleSelectPreset("knee")}
                retryLabel="Reset to Known Preset"
              />
            </Card>
          )}

          {/* STATE: Empty */}
          {screenState === "empty" && (
            <Card className="border-slate-200 bg-white p-12 text-center">
              <EmptyState
                title="No Active Cost Simulation"
                description="Select a treatment preset or adjust the parameters to compute insurance coverage and patient out-of-pocket costs."
                actionLabel="Calculate Knee Replacement"
                onAction={() => handleSelectPreset("knee")}
              />
            </Card>
          )}

          {/* STATE: Success or Not Determined */}
          {(screenState === "success" || screenState === "not_determined") && (
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
              {/* Left 5 Columns: Input Controls Form */}
              <div className="lg:col-span-5 space-y-6">
                <Card className="border-slate-200 shadow-sm bg-white">
                  <CardHeader>
                    <div className="flex items-center justify-between">
                      <CardTitle className="text-base">Treatment & Policy Inputs</CardTitle>
                      {isCalculating && (
                        <span className="text-[11px] font-mono text-[#0052D1] flex items-center gap-1">
                          <span className="w-2 h-2 rounded-full bg-[#0052D1] animate-ping" />
                          Computing...
                        </span>
                      )}
                    </div>
                    <CardDescription>
                      Customize hospital billing variables and coverage caps.
                    </CardDescription>
                  </CardHeader>

                  <CardContent className="space-y-4">
                    {/* Treatment Name */}
                    <div className="space-y-1.5">
                      <label htmlFor="treatment-name-input" className="text-xs font-semibold text-slate-700 block">
                        Treatment / Procedure Name
                      </label>
                      <input
                        id="treatment-name-input"
                        type="text"
                        value={treatmentName}
                        onChange={(e) => setTreatmentName(e.target.value)}
                        className="w-full text-xs sm:text-sm px-3.5 py-2 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-[#1769FF] font-medium"
                      />
                    </div>

                    {/* Hospital Quote */}
                    <div className="space-y-1.5">
                      <div className="flex justify-between items-center">
                        <label htmlFor="hospital-quote-slider" className="text-xs font-semibold text-slate-700">
                          Hospital Tariff / Billed Quote (₹)
                        </label>
                        <span className="font-mono text-xs font-bold text-[#0052D1]">
                          ₹{hospitalQuote.toLocaleString("en-IN")}
                        </span>
                      </div>
                      <input
                        id="hospital-quote-slider"
                        type="range"
                        min={10000}
                        max={600000}
                        step={5000}
                        value={hospitalQuote}
                        onChange={(e) => setHospitalQuote(Number(e.target.value))}
                        className="w-full accent-[#0052D1] cursor-pointer"
                        aria-label="Hospital Tariff Billed Quote"
                      />
                      <div className="flex justify-between text-[10px] text-slate-400 font-mono">
                        <span>₹10,000</span>
                        <span>₹3,00,000</span>
                        <span>₹6,00,000</span>
                      </div>
                    </div>

                    {/* Room Category */}
                    <div className="space-y-1.5">
                      <label htmlFor="room-category-select" className="text-xs font-semibold text-slate-700 block">
                        Selected Room Category
                      </label>
                      <select
                        id="room-category-select"
                        value={roomCategory}
                        onChange={(e) => setRoomCategory(e.target.value)}
                        className="w-full text-xs sm:text-sm px-3.5 py-2 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-[#1769FF] bg-white cursor-pointer"
                      >
                        <option value="Single Private Room">
                          Single Private Room
                        </option>
                        <option value="Shared Twin Room">
                          Shared Twin Room
                        </option>
                        <option value="Deluxe Suite">
                          Deluxe Suite
                        </option>
                        <option value="Daycare (No Room Charge)">
                          Daycare Procedure (No Room Fee)
                        </option>
                      </select>
                    </div>

                    {/* Annual Deductible & Copay */}
                    <div className="grid grid-cols-2 gap-3">
                      <div className="space-y-1.5">
                        <label htmlFor="deductible-input" className="text-xs font-semibold text-slate-700 block">
                          Deductible (₹)
                        </label>
                        <input
                          id="deductible-input"
                          type="number"
                          value={deductible}
                          onChange={(e) => setDeductible(Number(e.target.value))}
                          className="w-full text-xs sm:text-sm px-3 py-2 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-[#1769FF] font-mono"
                        />
                      </div>

                      <div className="space-y-1.5">
                        <label htmlFor="copay-input" className="text-xs font-semibold text-slate-700 block">
                          Copay (%)
                        </label>
                        <input
                          id="copay-input"
                          type="number"
                          min={0}
                          max={50}
                          value={copayPercent}
                          onChange={(e) => setCopayPercent(Number(e.target.value))}
                          className="w-full text-xs sm:text-sm px-3 py-2 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-[#1769FF] font-mono"
                        />
                      </div>
                    </div>

                    {/* Coverage Limit & Consumables */}
                    <div className="grid grid-cols-2 gap-3">
                      <div className="space-y-1.5">
                        <label htmlFor="limit-input" className="text-xs font-semibold text-slate-700 block">
                          Sum Insured (₹)
                        </label>
                        <input
                          id="limit-input"
                          type="number"
                          value={coverageLimit}
                          onChange={(e) => setCoverageLimit(Number(e.target.value))}
                          className="w-full text-xs sm:text-sm px-3 py-2 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-[#1769FF] font-mono"
                        />
                      </div>

                      <div className="space-y-1.5">
                        <label htmlFor="consumables-input" className="text-xs font-semibold text-slate-700 block">
                          Consumables Est. (₹)
                        </label>
                        <input
                          id="consumables-input"
                          type="number"
                          value={consumables}
                          onChange={(e) => setConsumables(Number(e.target.value))}
                          className="w-full text-xs sm:text-sm px-3 py-2 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-[#1769FF] font-mono"
                        />
                      </div>
                    </div>
                  </CardContent>

                  <CardFooter className="flex items-center justify-between">
                    <Button
                      variant="ghost"
                      size="xs"
                      onClick={() => handleSelectPreset("knee")}
                      leftIcon={<RotateCcw className="w-3.5 h-3.5" />}
                    >
                      Reset Defaults
                    </Button>
                    <StatusBadge variant="deterministic_calc" size="xs" label="Backend Rules" />
                  </CardFooter>
                </Card>
              </div>

              {/* Right 7 Columns: Visual Cost Breakdown & Recharts */}
              <div className="lg:col-span-7 space-y-6">
                {/* Top Result Banner */}
                <div className="p-6 rounded-2xl bg-white border border-slate-200 shadow-sm flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                  <div>
                    <div className="flex items-center gap-2 mb-1">
                      <Badge variant="teal" size="xs">
                        Policy Calculation
                      </Badge>
                      <span className="text-xs text-slate-500 font-mono">
                        {screenState === "not_determined"
                          ? "Not Determined"
                          : `${calculation?.effectivePercent ?? 0}% Covered`}
                      </span>
                    </div>
                    <h3 className="text-xl font-bold text-[#0A1D2E] tracking-tight">
                      Estimated Patient Liability:{" "}
                      <span className="text-[#B45309] font-mono font-extrabold">
                        {screenState === "not_determined"
                          ? "Not Determined"
                          : formatCurrency(calculation?.patientShare)}
                      </span>
                    </h3>
                  </div>

                  <div className="text-left sm:text-right">
                    <span className="text-xs text-slate-400 block uppercase font-semibold">
                      Insurer Obligation
                    </span>
                    <span className="font-mono text-xl font-extrabold text-[#006B5F]">
                      {screenState === "not_determined"
                        ? "Not Determined"
                        : formatCurrency(calculation?.insuranceShare)}
                    </span>
                  </div>
                </div>

                {/* Financial Numeric Metric Cards */}
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                  <MetricCard
                    label="Total Cost"
                    value={screenState === "not_determined" ? "Not Determined" : formatCurrency(calculation?.totalCost)}
                    sourceTier="policy_source"
                    sourceLabel="Quotation"
                    className="p-3.5"
                  />
                  <MetricCard
                    label="Deductible"
                    value={screenState === "not_determined" ? "Not Determined" : formatCurrency(calculation?.deductiblePaid)}
                    sourceTier="policy_source"
                    sourceLabel="Clause"
                    className="p-3.5"
                  />
                  <MetricCard
                    label="Copay Paid"
                    value={screenState === "not_determined" ? "Not Determined" : formatCurrency(calculation?.copayPaid)}
                    sourceTier="deterministic_calc"
                    sourceLabel={`${copayPercent}% Rule`}
                    className="p-3.5"
                  />
                  <MetricCard
                    label="Non-Payables"
                    value={screenState === "not_determined" ? "Not Determined" : formatCurrency(calculation?.nonPayableTotal)}
                    sourceTier="estimated_result"
                    sourceLabel="Excluded"
                    className="p-3.5"
                  />
                </div>

                {/* Stacked Cost Bar Visualization */}
                <Card className="border-slate-200 shadow-sm bg-white p-6 space-y-4">
                  <div className="flex justify-between items-center text-xs">
                    <span className="font-bold uppercase tracking-wider text-slate-600">
                      Stacked Cost Share Distribution
                    </span>
                    <span className="text-slate-400 font-mono text-[11px]">
                      {calculation?.rulesEngineVersion || "Rules Engine v2.4"}
                    </span>
                  </div>

                  {/* Multi-segment stacked bar */}
                  {calculation && calculation.totalCost > 0 ? (
                    <div className="w-full h-5 rounded-full overflow-hidden flex bg-slate-100 p-0.5">
                      <div
                        style={{ width: `${(calculation.insuranceShare / calculation.totalCost) * 100}%` }}
                        className="h-full bg-[#006B5F] rounded-l-full transition-all duration-300"
                        title={`Insurance: ${formatCurrency(calculation.insuranceShare)}`}
                      />
                      <div
                        style={{ width: `${(calculation.copayPaid / calculation.totalCost) * 100}%` }}
                        className="h-full bg-[#0052D1] transition-all duration-300"
                        title={`Co-pay: ${formatCurrency(calculation.copayPaid)}`}
                      />
                      <div
                        style={{ width: `${(calculation.deductiblePaid / calculation.totalCost) * 100}%` }}
                        className="h-full bg-[#D97706] transition-all duration-300"
                        title={`Deductible: ${formatCurrency(calculation.deductiblePaid)}`}
                      />
                      <div
                        style={{ width: `${(calculation.nonPayableTotal / calculation.totalCost) * 100}%` }}
                        className="h-full bg-[#BA1A1A] rounded-r-full transition-all duration-300"
                        title={`Non-Payables: ${formatCurrency(calculation.nonPayableTotal)}`}
                      />
                    </div>
                  ) : (
                    <div className="w-full h-5 rounded-full bg-slate-100 flex items-center justify-center text-[10px] text-slate-400">
                      No distribution available
                    </div>
                  )}

                  {/* Legend */}
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs pt-1">
                    <div className="flex items-center gap-1.5">
                      <span className="w-3 h-3 rounded-sm bg-[#006B5F] shrink-0" />
                      <span className="text-slate-600 truncate">Insurer Share</span>
                    </div>
                    <div className="flex items-center gap-1.5">
                      <span className="w-3 h-3 rounded-sm bg-[#0052D1] shrink-0" />
                      <span className="text-slate-600 truncate">Copay Share</span>
                    </div>
                    <div className="flex items-center gap-1.5">
                      <span className="w-3 h-3 rounded-sm bg-[#D97706] shrink-0" />
                      <span className="text-slate-600 truncate">Deductible</span>
                    </div>
                    <div className="flex items-center gap-1.5">
                      <span className="w-3 h-3 rounded-sm bg-[#BA1A1A] shrink-0" />
                      <span className="text-slate-600 truncate">Non-Payables</span>
                    </div>
                  </div>
                </Card>

                {/* Recharts Pie Breakdown */}
                <Card className="border-slate-200 shadow-sm bg-white p-6">
                  <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
                    <div className="w-full sm:w-1/2 h-52 flex items-center justify-center">
                      {chartData.length > 0 ? (
                        <ResponsiveContainer width="100%" height="100%">
                          <PieChart>
                            <Pie
                              data={chartData}
                              dataKey="value"
                              nameKey="name"
                              cx="50%"
                              cy="50%"
                              innerRadius={50}
                              outerRadius={80}
                              paddingAngle={3}
                            >
                              {chartData.map((entry, index) => (
                                <Cell key={`cell-${index}`} fill={entry.color} />
                              ))}
                            </Pie>
                            <RechartsTooltip
                              formatter={(val: unknown) => [
                                formatCurrency(Number(val)),
                                "",
                              ]}
                            />
                          </PieChart>
                        </ResponsiveContainer>
                      ) : (
                        <div className="text-xs text-slate-400">Not Determined</div>
                      )}
                    </div>

                    <div className="w-full sm:w-1/2 divide-y divide-slate-100 text-xs">
                      <div className="py-2 flex justify-between">
                        <span className="text-slate-600">Billed Hospital Estimate:</span>
                        <span className="font-mono font-bold text-slate-900">
                          {formatCurrency(calculation?.totalCost)}
                        </span>
                      </div>
                      <div className="py-2 flex justify-between">
                        <span className="text-slate-600">Contracted Tariff (Negotiated):</span>
                        <span className="font-mono text-slate-800">
                          {formatCurrency(calculation?.contractedAllowance)}
                        </span>
                      </div>
                      <div className="py-2 flex justify-between">
                        <span className="text-slate-600">Deductible Applied:</span>
                        <span className="font-mono text-amber-700">
                          {formatCurrency(calculation?.deductiblePaid)}
                        </span>
                      </div>
                      <div className="py-2 flex justify-between">
                        <span className="text-slate-600">Co-Pay ({copayPercent}%):</span>
                        <span className="font-mono text-blue-700">
                          {formatCurrency(calculation?.copayPaid)}
                        </span>
                      </div>
                      {calculation && calculation.roomRentPenaltyAmount > 0 && (
                        <div className="py-2 flex justify-between text-rose-700">
                          <span>Room Rent Penalty (Deluxe):</span>
                          <span className="font-mono font-semibold">
                            +{formatCurrency(calculation.roomRentPenaltyAmount)}
                          </span>
                        </div>
                      )}
                      <div className="py-2 flex justify-between">
                        <span className="text-slate-600">Consumables (Non-Admissible):</span>
                        <span className="font-mono text-rose-700">
                          +{formatCurrency(consumables)}
                        </span>
                      </div>
                    </div>
                  </div>
                </Card>

                {/* Estimate Disclaimer */}
                <div className="p-4 rounded-xl bg-[#FFFBEB] border border-amber-200 text-xs text-[#92400E] flex items-start gap-2.5">
                  <Info className="w-4 h-4 shrink-0 text-amber-600 mt-0.5" />
                  <p className="leading-relaxed">
                    <strong>Simulation Disclaimer:</strong> CoverWise AI provides informational estimates based
                    on available policy information and user-provided treatment costs. It does not provide insurer
                    authorization or guarantee claim payment.
                  </p>
                </div>
              </div>
            </div>
          )}
        </div>
      </main>

      <Footer />
    </div>
  );
}

export default function SimulatorPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen flex items-center justify-center bg-[#F8F9FF]">
          <div className="w-8 h-8 border-3 border-[#0052D1] border-t-transparent rounded-full animate-spin" />
        </div>
      }
    >
      <SimulatorContent />
    </Suspense>
  );
}

