"use client";

import React, { useState } from "react";
import { SectionHeader } from "@/components/ui/SectionHeader";
import { MetricCard } from "@/components/ui/MetricCard";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/Card";
import { StatusBadge } from "@/components/ui/StatusBadge";
import {
  Shield,
  FileCheck,
  Info,
  Calculator,
  TrendingUp,
} from "lucide-react";

interface TreatmentScenario {
  id: string;
  name: string;
  category: string;
  currency: string;
  billedEstimate: number;
  allowedRate: number;
  deductibleApplied: number;
  coinsuranceRate: number;
  coinsuranceAmount: number;
  patientTotal: number;
  insurerTotal: number;
  clauseRef: string;
  clauseText: string;
}

const scenarios: TreatmentScenario[] = [
  {
    id: "knee-inr",
    name: "Total Knee Replacement (Inpatient)",
    category: "Inpatient Orthopedic Surgery",
    currency: "₹",
    billedEstimate: 260000,
    allowedRate: 235000,
    deductibleApplied: 15000,
    coinsuranceRate: 10,
    coinsuranceAmount: 23500,
    patientTotal: 38500,
    insurerTotal: 221500,
    clauseRef: "Policy Schedule §4.3: Joint Replacement Coverage",
    clauseText:
      "Subject to room-rent capping of ₹5,000/day. Co-payment of 10% applies to major orthopedic surgeries. Implant charges subject to standard ceiling tariff.",
  },
  {
    id: "mri-inr",
    name: "MRI Brain with Contrast",
    category: "Advanced Diagnostic Imaging",
    currency: "₹",
    billedEstimate: 22000,
    allowedRate: 16500,
    deductibleApplied: 2500,
    coinsuranceRate: 15,
    coinsuranceAmount: 2100,
    patientTotal: 4600,
    insurerTotal: 17400,
    clauseRef: "Diagnostic Rider §2.1: In-Network Scans",
    clauseText:
      "Diagnostic MRI/CT scans covered at 85% of contracted network rates following primary physician referral.",
  },
  {
    id: "knee-usd",
    name: "Knee Arthroscopy (Outpatient USD)",
    category: "Ambulatory Surgery",
    currency: "$",
    billedEstimate: 4200,
    allowedRate: 2800,
    deductibleApplied: 650,
    coinsuranceRate: 20,
    coinsuranceAmount: 430,
    patientTotal: 1080,
    insurerTotal: 1720,
    clauseRef: "SBC Section 4.2: Ambulatory Surgical Centers",
    clauseText:
      "Covered at 80% of allowed charges after individual annual deductible has been satisfied. Pre-authorization required.",
  },
];

export function DashboardPreviewSection() {
  const [selectedId, setSelectedId] = useState<string>("knee-inr");
  const activeScenario = scenarios.find((s) => s.id === selectedId) || scenarios[0];
  const cur = activeScenario.currency;

  const formatMoney = (val: number) => {
    return `${cur}${val.toLocaleString("en-IN")}`;
  };

  return (
    <section id="coverage-intelligence" className="py-16 sm:py-24 bg-[#F8F9FF] border-b border-slate-200/60">
      <div id="treatment-costs" />
      <div id="dashboard" />
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <SectionHeader
          badge="Coverage Intelligence Dashboard"
          badgeVariant="primary"
          title="Treatment Cost & Policy Intelligence"
          description="Explore how policy terms, deductible thresholds, and coinsurance formulas apply to specific treatments."
          align="left"
        />

        {/* Treatment Scenario Selector Tabs */}
        <div className="flex flex-wrap items-center gap-2 mb-8">
          {scenarios.map((sc) => {
            const isSelected = sc.id === selectedId;
            return (
              <button
                key={sc.id}
                onClick={() => setSelectedId(sc.id)}
                className={`text-xs sm:text-sm font-medium px-4 py-2.5 rounded-xl border transition-all cursor-pointer ${
                  isSelected
                    ? "bg-[#0052D1] text-white border-[#0052D1] shadow-sm"
                    : "bg-white text-slate-700 border-slate-200 hover:border-blue-200 hover:bg-[#EEF4FF]"
                }`}
              >
                {sc.name}
              </button>
            );
          })}
        </div>

        {/* Top Metric Cards Row */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          <MetricCard
            label="Total Est. Treatment"
            value={formatMoney(activeScenario.billedEstimate)}
            sourceTier="policy_source"
            sourceLabel="Hospital Quotation"
            subtext="Baseline procedure tariff"
            icon={<TrendingUp className="w-5 h-5 text-slate-600" />}
          />

          <MetricCard
            label="In-Network Allowed"
            value={formatMoney(activeScenario.allowedRate)}
            sourceTier="deterministic_calc"
            sourceLabel="Contracted Rate"
            subtext="Negotiated network ceiling"
            icon={<Shield className="w-5 h-5" />}
          />

          <MetricCard
            label="Insurance Estimated Share"
            value={formatMoney(activeScenario.insurerTotal)}
            sourceTier="deterministic_calc"
            sourceLabel="Deterministic Math"
            subtext="Covered benefit obligation"
            icon={<Calculator className="w-5 h-5 text-[#006B5F]" />}
          />

          <MetricCard
            label="Patient Liability"
            value={formatMoney(activeScenario.patientTotal)}
            sourceTier="estimated_result"
            sourceLabel="Patient Estimate"
            subtext="Provisional out-of-pocket"
            highlight
            icon={<FileCheck className="w-5 h-5 text-[#0052D1]" />}
          />
        </div>

        {/* Detailed Breakdown Card and Clause Audit Box */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
          {/* Left Column: Calculation Breakdown (7 cols) */}
          <div className="lg:col-span-7">
            <Card className="shadow-sm">
              <CardHeader className="flex flex-row items-center justify-between">
                <div>
                  <CardTitle>Deterministic Cost Computation</CardTitle>
                  <CardDescription>
                    Audited formula breakdown for {activeScenario.name}
                  </CardDescription>
                </div>
                <StatusBadge variant="deterministic_calc" size="xs" label="Verified Math" />
              </CardHeader>

              <CardContent className="space-y-4">
                <div className="divide-y divide-slate-100 text-xs">
                  <div className="py-3 flex justify-between items-center">
                    <span className="text-slate-600 font-medium">Billed Hospital Estimate:</span>
                    <span className="font-mono text-slate-800 font-semibold">
                      {formatMoney(activeScenario.billedEstimate)}
                    </span>
                  </div>

                  <div className="py-3 flex justify-between items-center">
                    <div className="flex items-center gap-1.5">
                      <span className="text-slate-600 font-medium">In-Network Contract Allowance:</span>
                      <StatusBadge variant="deterministic_calc" size="xs" label="Engine" />
                    </div>
                    <span className="font-mono text-slate-900 font-semibold">
                      {formatMoney(activeScenario.allowedRate)}
                    </span>
                  </div>

                  <div className="py-3 flex justify-between items-center">
                    <div className="flex items-center gap-1.5">
                      <span className="text-slate-600 font-medium">Deductible Applied:</span>
                      <StatusBadge variant="policy_source" size="xs" label="Clause" />
                    </div>
                    <span className="font-mono text-amber-700 font-semibold">
                      {formatMoney(activeScenario.deductibleApplied)}
                    </span>
                  </div>

                  <div className="py-3 flex justify-between items-center">
                    <div className="flex items-center gap-1.5">
                      <span className="text-slate-600 font-medium">
                        Patient Co-Payment ({activeScenario.coinsuranceRate}% of remaining):
                      </span>
                      <StatusBadge variant="deterministic_calc" size="xs" label="Formula" />
                    </div>
                    <span className="font-mono text-amber-700 font-semibold">
                      {formatMoney(activeScenario.coinsuranceAmount)}
                    </span>
                  </div>
                </div>

                {/* Final Total Box */}
                <div className="p-4 rounded-xl bg-gradient-to-r from-[#EEF4FF] to-[#E6F7F5] border border-blue-200/80 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                  <div>
                    <span className="text-xs font-semibold uppercase tracking-wider text-[#0052D1]">
                      Estimated Patient Liability (Demo)
                    </span>
                    <p className="text-[11px] text-slate-600">
                      Deductible ({formatMoney(activeScenario.deductibleApplied)}) + Co-payment (
                      {formatMoney(activeScenario.coinsuranceAmount)})
                    </p>
                  </div>
                  <div className="text-left sm:text-right">
                    <span className="font-mono text-2xl font-bold text-[#0052D1]">
                      {formatMoney(activeScenario.patientTotal)}
                    </span>
                    <span className="block text-[10px] text-slate-500 uppercase font-mono">
                      Provisional Estimate
                    </span>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Right Column: Policy Source & Audit Clause (5 cols) */}
          <div className="lg:col-span-5 flex flex-col gap-4">
            <Card className="border-l-4 border-l-[#0052D1] bg-white shadow-sm">
              <CardHeader className="pb-3">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold uppercase tracking-wider text-[#0052D1]">
                    Auditable Policy Clause
                  </span>
                  <StatusBadge variant="policy_source" size="xs" label="Verified Source" />
                </div>
                <CardTitle className="text-sm mt-1">
                  {activeScenario.clauseRef}
                </CardTitle>
              </CardHeader>

              <CardContent className="space-y-3 pt-0">
                <div className="p-3.5 rounded-xl bg-[#F8F9FF] border border-blue-100 text-xs text-slate-700 leading-relaxed italic">
                  “{activeScenario.clauseText}”
                </div>

                <div className="space-y-1 text-xs text-slate-500">
                  <div className="flex justify-between py-1 border-b border-slate-100">
                    <span>Document Source:</span>
                    <span className="font-medium text-slate-800">Policy_Schedule_2026.pdf</span>
                  </div>
                  <div className="flex justify-between py-1 border-b border-slate-100">
                    <span>Category:</span>
                    <span className="font-medium text-slate-800">{activeScenario.category}</span>
                  </div>
                  <div className="flex justify-between py-1">
                    <span>Deterministic Extraction:</span>
                    <span className="font-mono font-medium text-emerald-600">Verified Rule</span>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Disclaimer box */}
            <div className="p-4 rounded-xl bg-[#FFFBEB] border border-amber-200 text-xs text-[#92400E] flex items-start gap-2.5">
              <Info className="w-4 h-4 shrink-0 mt-0.5 text-amber-600" />
              <p className="leading-relaxed">
                <strong>Estimate Disclaimer:</strong> CoverWise AI provides informational estimates based
                on available policy information and user-provided treatment costs. It does not provide insurer
                authorization or guarantee claim payment.
              </p>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
