"use client";

import React, { useState, useCallback } from "react";
import Link from "next/link";
import { Header } from "@/components/layout/Header";
import { Footer } from "@/components/layout/Footer";
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { MetricCard } from "@/components/ui/MetricCard";
import { LoadingState } from "@/components/ui/LoadingState";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorState } from "@/components/ui/ErrorState";
import { api, parseApiError } from "@/lib/api";
import { DEMO_DASHBOARD_OVERVIEW } from "@/lib/mock-data";
import {
  DashboardOverview,
  CoverageStatus,
  RecentAnalysisRecord,
  ApiError,
} from "@/types";
import {
  formatCurrency,
  displayValueOrNotDetermined,
} from "@/lib/utils";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";
import {
  FileText,
  Activity,
  Coins,
  Shield,
  Plus,
  Search,
  CheckCircle2,
  HelpCircle,
  XCircle,
} from "lucide-react";

type DashboardState = "success" | "loading" | "empty" | "error" | "not_determined";

export default function DashboardPage() {
  const [state, setState] = useState<DashboardState>("success");
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [dashboardData, setDashboardData] = useState<DashboardOverview | null>(DEMO_DASHBOARD_OVERVIEW);
  const [apiError, setApiError] = useState<ApiError | null>(null);

  const loadDashboard = useCallback(async () => {
    setState("loading");
    setApiError(null);

    try {
      const data = await api.getDashboardOverview();
      setDashboardData(data);
      setState("success");
    } catch (err) {
      setApiError(parseApiError(err));
      setState("error");
    }
  }, []);

  const activeRecords: RecentAnalysisRecord[] =
    state === "not_determined"
      ? [
          {
            id: "rec-undetermined-1",
            policy: "Pending Verification Plan",
            treatment: "Stem Cell Cartilage Repair",
            hospital: "City Specialty Hospital",
            estimatedCost: null,
            estimatedPatientShare: null,
            status: "Not Determined",
            date: "Today",
          },
        ]
      : dashboardData?.recentAnalyses || [];

  const filteredRecords = activeRecords.filter((r) => {
    const matchesSearch =
      r.treatment.toLowerCase().includes(searchQuery.toLowerCase()) ||
      r.policy.toLowerCase().includes(searchQuery.toLowerCase()) ||
      r.hospital.toLowerCase().includes(searchQuery.toLowerCase());

    const matchesStatus =
      statusFilter === "all" || r.status.toLowerCase().includes(statusFilter.toLowerCase());

    return matchesSearch && matchesStatus;
  });

  const renderStatusBadge = (status: CoverageStatus | undefined) => {
    switch (status) {
      case "Likely Covered":
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-[#ECFDF5] text-[#065F46] border border-emerald-200">
            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
            Likely Covered
          </span>
        );
      case "Partially Covered":
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-[#EFF6FF] text-[#1E40AF] border border-blue-200">
            <HelpCircle className="w-3.5 h-3.5 text-blue-600" />
            Partially Covered
          </span>
        );
      case "Not Covered":
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-[#FEF2F2] text-[#991B1B] border border-rose-200">
            <XCircle className="w-3.5 h-3.5 text-rose-600" />
            Not Covered
          </span>
        );
      case "Not Determined":
      default:
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-slate-100 text-slate-700 border border-slate-200">
            Not Determined
          </span>
        );
    }
  };

  const activePolicy = dashboardData?.activePolicy;

  return (
    <div className="min-h-screen flex flex-col bg-[#F8F9FF] text-[#0A1D2E] antialiased">
      <Header />

      <main className="flex-1 py-10 sm:py-16">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 space-y-8">
          {/* Header & State Controls */}
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div>
              <div className="flex items-center gap-2 text-xs text-slate-500 mb-1">
                <Link href="/" className="hover:text-[#0052D1]">
                  Home
                </Link>
                <span>/</span>
                <span className="font-semibold text-slate-800">Intelligence Dashboard</span>
              </div>
              <h1 className="text-2xl sm:text-3xl font-extrabold text-[#0A1D2E] tracking-tight">
                Coverage Intelligence Dashboard
              </h1>
            </div>

            {/* Interactive Demo State Toggles */}
            <div className="flex flex-wrap items-center gap-2 p-1 rounded-xl bg-white border border-slate-200 shadow-xs">
              <span className="text-[11px] font-semibold text-slate-400 px-2 uppercase">
                Dashboard State:
              </span>
              {(["success", "loading", "empty", "error", "not_determined"] as DashboardState[]).map((s) => (
                <button
                  key={s}
                  onClick={() => {
                    if (s === "success") {
                      loadDashboard();
                    } else if (s === "error") {
                      setApiError({
                        statusCode: 504,
                        code: "GATEWAY_TIMEOUT",
                        message: "The intelligence database timed out while aggregating coverage history.",
                        details: "Downstream reporting service did not respond within 15000ms.",
                        timestamp: new Date().toISOString(),
                      });
                      setState("error");
                    } else {
                      setState(s);
                    }
                  }}
                  className={`text-xs px-2.5 py-1 rounded-lg capitalize font-medium transition-colors cursor-pointer ${
                    state === s
                      ? "bg-[#0052D1] text-white"
                      : "text-slate-600 hover:bg-slate-100"
                  }`}
                >
                  {s.replace("_", " ")}
                </button>
              ))}
            </div>
          </div>

          {/* STATE: Loading */}
          {state === "loading" && (
            <div className="space-y-6">
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                <LoadingState variant="skeleton" lines={2} className="p-6 bg-white rounded-2xl border" />
                <LoadingState variant="skeleton" lines={2} className="p-6 bg-white rounded-2xl border" />
                <LoadingState variant="skeleton" lines={2} className="p-6 bg-white rounded-2xl border" />
                <LoadingState variant="skeleton" lines={2} className="p-6 bg-white rounded-2xl border" />
              </div>
              <LoadingState
                variant="card"
                message="Loading policy intelligence analytics..."
                subtext="Compiling deterministic calculation history and procedure estimates from API client"
              />
            </div>
          )}

          {/* STATE: Empty */}
          {state === "empty" && (
            <Card className="p-8 sm:p-14 bg-white border-slate-200 text-center">
              <EmptyState
                icon={<FileText className="w-8 h-8 text-slate-400" />}
                title="No Policies Analyzed Yet"
                description="Upload an insurance policy document or run a demo scenario to see your personalized coverage intelligence, cost charts, and patient liability history."
                action={
                  <div className="flex flex-wrap items-center justify-center gap-3">
                    <Link href="/analyze">
                      <Button variant="primary" size="md" leftIcon={<Plus className="w-4 h-4" />}>
                        Upload Policy Document
                      </Button>
                    </Link>
                    <Button variant="outline" size="md" onClick={() => loadDashboard()}>
                      Load Sample Dashboard
                    </Button>
                  </div>
                }
              />
            </Card>
          )}

          {/* STATE: Error */}
          {state === "error" && (
            <Card className="p-8 bg-white border-red-200">
              <ErrorState
                title="Failed to Load Dashboard Analytics"
                message={apiError?.message || "We encountered an issue synchronizing your recent coverage analysis records."}
                details={
                  apiError?.details
                    ? typeof apiError.details === "string"
                      ? apiError.details
                      : JSON.stringify(apiError.details)
                    : `Error Code: ${apiError?.code || "DB_TIMEOUT"} • Status: ${apiError?.statusCode || 500}`
                }
                onRetry={loadDashboard}
                retryLabel="Reload Dashboard"
              />
            </Card>
          )}

          {/* STATE: Success or Not Determined */}
          {(state === "success" || state === "not_determined") && (
            <div className="space-y-8">
              {/* 1. Top 4 Metric Cards */}
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                <MetricCard
                  label="Policies Analyzed"
                  value={state === "not_determined" ? "Not Determined" : `${dashboardData?.policiesAnalyzedCount || 3} Active`}
                  sourceTier="policy_source"
                  sourceLabel="Document Ingestion"
                  subtext="Care Health, Star, HDFC ERGO"
                  icon={<FileText className="w-5 h-5 text-[#0052D1]" />}
                />

                <MetricCard
                  label="Coverage Analyses"
                  value={state === "not_determined" ? "Not Determined" : `${dashboardData?.coverageAnalysesCount || 14} Done`}
                  sourceTier="deterministic_calc"
                  sourceLabel="Rules Engine"
                  subtext="Orthopedic, Ophthalmology, Radiology"
                  icon={<Activity className="w-5 h-5 text-[#006B5F]" />}
                />

                <MetricCard
                  label="Estimated Patient Costs"
                  value={state === "not_determined" ? "Not Determined" : formatCurrency(dashboardData?.totalEstimatedPatientCosts)}
                  sourceTier="estimated_result"
                  sourceLabel="Cumulative Est."
                  subtext="Deductible & copays across care"
                  icon={<Coins className="w-5 h-5 text-[#D97706]" />}
                />

                <MetricCard
                  label="Recent Analysis"
                  value={state === "not_determined" ? "Not Determined" : "₹38,500"}
                  sourceTier="estimated_result"
                  sourceLabel="Knee Replacement"
                  subtext="Total Knee Arthroplasty (Demo)"
                  highlight
                  icon={<Shield className="w-5 h-5 text-[#0052D1]" />}
                />
              </div>

              {/* 2. Middle Row: Cost Chart + Policy Rules Section */}
              <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
                {/* Cost Chart (7 cols) */}
                <div className="lg:col-span-7">
                  <Card className="border-slate-200 shadow-sm bg-white p-6">
                    <div className="flex items-center justify-between mb-4">
                      <div>
                        <h3 className="text-base font-bold text-[#0A1D2E]">
                          Treatment Cost Analysis Comparison
                        </h3>
                        <p className="text-xs text-slate-500">
                          Estimated Insurer Share vs Patient Liability across evaluated treatments
                        </p>
                      </div>
                      <Badge variant="teal" size="xs">
                        ₹ Currency
                      </Badge>
                    </div>

                    <div className="w-full h-72">
                      {dashboardData?.costComparisonChart && dashboardData.costComparisonChart.length > 0 ? (
                        <ResponsiveContainer width="100%" height="100%">
                          <BarChart
                            data={dashboardData.costComparisonChart}
                            margin={{ top: 10, right: 10, left: 10, bottom: 20 }}
                          >
                            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#E2E8F0" />
                            <XAxis
                              dataKey="name"
                              tick={{ fontSize: 11, fill: "#64748B" }}
                              interval={0}
                              angle={-12}
                              textAnchor="end"
                            />
                            <YAxis
                              tick={{ fontSize: 10, fill: "#64748B" }}
                              tickFormatter={(v) => `₹${(v / 1000).toFixed(0)}k`}
                            />
                            <RechartsTooltip
                              formatter={(value: unknown, name: unknown) => [
                                formatCurrency(Number(value)),
                                name === "insurer" ? "Insurer Share" : "Patient Share",
                              ]}
                            />
                            <Legend
                              wrapperStyle={{ paddingTop: 10, fontSize: 12 }}
                              formatter={(val) => (val === "insurer" ? "Estimated Insurer Share" : "Estimated Patient Share")}
                            />
                            <Bar dataKey="insurer" fill="#006B5F" radius={[4, 4, 0, 0]} />
                            <Bar dataKey="patient" fill="#0052D1" radius={[4, 4, 0, 0]} />
                          </BarChart>
                        </ResponsiveContainer>
                      ) : (
                        <div className="w-full h-full flex items-center justify-center text-xs text-slate-400">
                          No chart data available
                        </div>
                      )}
                    </div>
                  </Card>
                </div>

                {/* Active Coverage Summary & Policy Rules (5 cols) */}
                <div className="lg:col-span-5 space-y-4">
                  <Card className="border-slate-200 shadow-sm bg-white">
                    <CardHeader className="pb-3">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-bold uppercase tracking-wider text-[#0052D1]">
                          Primary Active Policy
                        </span>
                        <StatusBadge variant="policy_source" size="xs" label="Verified Active" />
                      </div>
                      <CardTitle className="text-base mt-1">
                        {displayValueOrNotDetermined(activePolicy?.planName)}
                      </CardTitle>
                      <CardDescription>
                        {displayValueOrNotDetermined(activePolicy?.insurerName)} • No:{" "}
                        {displayValueOrNotDetermined(activePolicy?.policyNumber)}
                      </CardDescription>
                    </CardHeader>

                    <CardContent className="space-y-3.5 pt-0">
                      <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200/80 space-y-2 text-xs">
                        <div className="flex justify-between">
                          <span className="text-slate-500">Annual Sum Insured:</span>
                          <span className="font-mono font-bold text-slate-900">
                            {formatCurrency(activePolicy?.sumInsured)}
                          </span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-slate-500">Individual Deductible:</span>
                          <span className="font-mono font-bold text-amber-700">
                            {formatCurrency(activePolicy?.deductible)}
                          </span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-slate-500">Pre-existing Waiting:</span>
                          <span className="font-medium text-emerald-700">
                            {activePolicy?.waitingPeriodMonths != null
                              ? `${activePolicy.waitingPeriodMonths} Months (Satisfied)`
                              : "Not Determined"}
                          </span>
                        </div>
                      </div>

                      {/* Policy Rules List */}
                      <div className="space-y-2 text-xs">
                        <span className="text-[11px] font-bold uppercase tracking-wider text-slate-500 block">
                          Key Policy Conditions & Caps:
                        </span>
                        <div className="space-y-1.5">
                          <div className="p-2.5 rounded-lg border border-slate-100 bg-white flex items-center justify-between">
                            <span className="font-medium text-slate-800">Room Rent Limit:</span>
                            <span className="text-slate-600 font-mono text-[11px]">
                              {displayValueOrNotDetermined(activePolicy?.roomRentLimit)}
                            </span>
                          </div>
                          <div className="p-2.5 rounded-lg border border-slate-100 bg-white flex items-center justify-between">
                            <span className="font-medium text-slate-800">Major Surgery Co-Pay:</span>
                            <span className="text-blue-700 font-mono text-[11px]">
                              {displayValueOrNotDetermined(activePolicy?.copayPercent, "", "% Mandated")}
                            </span>
                          </div>
                          <div className="p-2.5 rounded-lg border border-slate-100 bg-white flex items-center justify-between">
                            <span className="font-medium text-slate-800">Network Tier:</span>
                            <span className="text-emerald-700 font-mono text-[11px]">
                              {displayValueOrNotDetermined(activePolicy?.networkType)}
                            </span>
                          </div>
                        </div>
                      </div>

                      <Link href="/coverage" className="block pt-1">
                        <Button variant="outline" size="sm" className="w-full justify-center">
                          View Detailed Policy Intelligence
                        </Button>
                      </Link>
                    </CardContent>
                  </Card>
                </div>
              </div>

              {/* 3. Bottom Row: Recent Analyses Table */}
              <Card className="border-slate-200 shadow-sm bg-white overflow-hidden">
                <CardHeader className="border-b border-slate-100">
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                    <div>
                      <CardTitle className="text-base">Recent Coverage Analyses</CardTitle>
                      <CardDescription>
                        Historical procedure estimates, hospital quotations, and patient liability breakdowns.
                      </CardDescription>
                    </div>

                    {/* Search & Filter Controls */}
                    <div className="flex flex-wrap items-center gap-2">
                      <div className="relative">
                        <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
                        <input
                          type="text"
                          placeholder="Search treatment..."
                          value={searchQuery}
                          onChange={(e) => setSearchQuery(e.target.value)}
                          className="pl-8 pr-3 py-1.5 rounded-lg border border-slate-200 text-xs focus:outline-none focus:ring-2 focus:ring-[#1769FF] w-40 sm:w-48"
                          aria-label="Search recent treatments"
                        />
                      </div>

                      <select
                        value={statusFilter}
                        onChange={(e) => setStatusFilter(e.target.value)}
                        className="px-2.5 py-1.5 rounded-lg border border-slate-200 text-xs bg-white text-slate-700 focus:outline-none focus:ring-2 focus:ring-[#1769FF]"
                        aria-label="Filter by coverage status"
                      >
                        <option value="all">All Statuses</option>
                        <option value="Likely Covered">Likely Covered</option>
                        <option value="Partially Covered">Partially Covered</option>
                        <option value="Not Covered">Not Covered</option>
                        <option value="Not Determined">Not Determined</option>
                      </select>
                    </div>
                  </div>
                </CardHeader>

                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs">
                    <thead className="bg-slate-50 border-b border-slate-100 text-slate-500 font-semibold uppercase tracking-wider text-[11px]">
                      <tr>
                        <th className="px-6 py-3.5">Treatment & Procedure</th>
                        <th className="px-6 py-3.5">Policy Contract</th>
                        <th className="px-6 py-3.5">Hospital Network</th>
                        <th className="px-6 py-3.5">Estimated Cost</th>
                        <th className="px-6 py-3.5">Patient Share</th>
                        <th className="px-6 py-3.5">Status</th>
                        <th className="px-6 py-3.5">Date</th>
                        <th className="px-6 py-3.5 text-right">Actions</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                      {filteredRecords.length > 0 ? (
                        filteredRecords.map((r) => (
                          <tr key={r.id} className="hover:bg-slate-50/70 transition-colors">
                            <td className="px-6 py-4 font-bold text-[#0A1D2E]">
                              {displayValueOrNotDetermined(r.treatment)}
                            </td>
                            <td className="px-6 py-4 text-slate-600 truncate max-w-[160px]">
                              {displayValueOrNotDetermined(r.policy)}
                            </td>
                            <td className="px-6 py-4 text-slate-500 truncate max-w-[180px]">
                              {displayValueOrNotDetermined(r.hospital)}
                            </td>
                            <td className="px-6 py-4 font-mono font-semibold text-slate-900">
                              {formatCurrency(r.estimatedCost)}
                            </td>
                            <td className="px-6 py-4 font-mono font-bold text-[#0052D1]">
                              {formatCurrency(r.estimatedPatientShare)}
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap">
                              {renderStatusBadge(r.status)}
                            </td>
                            <td className="px-6 py-4 text-slate-400 whitespace-nowrap font-mono text-[11px]">
                              {displayValueOrNotDetermined(r.date)}
                            </td>
                            <td className="px-6 py-4 text-right whitespace-nowrap">
                              <Link href="/coverage">
                                <Button variant="outline" size="xs">
                                  Details
                                </Button>
                              </Link>
                            </td>
                          </tr>
                        ))
                      ) : (
                        <tr>
                          <td colSpan={8} className="px-6 py-8 text-center text-slate-400 text-xs">
                            No evaluations matched your search query.
                          </td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>

                <CardFooter className="flex items-center justify-between text-xs text-slate-500">
                  <span>
                    Showing {filteredRecords.length} evaluations
                  </span>
                  <Link href="/analyze">
                    <Button variant="primary" size="xs" leftIcon={<Plus className="w-3.5 h-3.5" />}>
                      Analyze New Document
                    </Button>
                  </Link>
                </CardFooter>
              </Card>
            </div>
          )}
        </div>
      </main>

      <Footer />
    </div>
  );
}
