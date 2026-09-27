"use client";

import React, { useState } from "react";
import { SectionHeader } from "@/components/ui/SectionHeader";
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { MetricCard } from "@/components/ui/MetricCard";
import { IconContainer } from "@/components/ui/IconContainer";
import { ProgressBar } from "@/components/ui/ProgressBar";
import { LoadingState } from "@/components/ui/LoadingState";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorState } from "@/components/ui/ErrorState";
import {
  FileText,
  Sparkles,
  Calculator,
  ShieldCheck,
  Coins,
  Receipt,
  Activity,
} from "lucide-react";

export function DesignSystemShowcase() {
  const [btnLoading, setBtnLoading] = useState(false);
  const progressVal = 65;

  return (
    <section className="py-16 sm:py-24 bg-white border-b border-slate-200/60" id="design-system">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <SectionHeader
          badge="Design System & UI Components"
          badgeVariant="teal"
          title="Foundational UI Component Library"
          description="Consistent, accessible, and audit-ready components tailored for policy documents, deterministic math, and healthcare estimates."
          align="left"
        />

        <div className="space-y-12">
          {/* 1. Buttons */}
          <div className="space-y-4">
            <h3 className="text-sm font-bold uppercase tracking-wider text-slate-500">
              1. Buttons & Interaction States
            </h3>
            <div className="p-6 rounded-2xl bg-slate-50 border border-slate-200 flex flex-wrap items-center gap-3">
              <Button variant="primary">Primary Action</Button>
              <Button variant="secondary">Secondary Navy</Button>
              <Button variant="teal">Teal Engine</Button>
              <Button variant="outline">Outline</Button>
              <Button variant="subtle">Subtle Blue</Button>
              <Button variant="ghost">Ghost Button</Button>
              <Button variant="danger">Danger / Action</Button>
              <Button
                variant="primary"
                isLoading={btnLoading}
                onClick={() => {
                  setBtnLoading(true);
                  setTimeout(() => setBtnLoading(false), 1500);
                }}
              >
                {btnLoading ? "Processing..." : "Click For Loading State"}
              </Button>
            </div>
          </div>

          {/* 2. Badges & Icon Containers */}
          <div className="space-y-4">
            <h3 className="text-sm font-bold uppercase tracking-wider text-slate-500">
              2. Badges & Icon Containers
            </h3>
            <div className="p-6 rounded-2xl bg-slate-50 border border-slate-200 flex flex-wrap items-center gap-4">
              <Badge variant="default" dot>Default Badge</Badge>
              <Badge variant="primary">Primary</Badge>
              <Badge variant="secondary">Navy</Badge>
              <Badge variant="teal">Teal Tag</Badge>
              <Badge variant="outline">Outline</Badge>
              <Badge variant="neutral">Neutral</Badge>

              <div className="h-6 w-px bg-slate-300 mx-2" />

              <IconContainer variant="primary" size="md">
                <FileText className="w-5 h-5" />
              </IconContainer>
              <IconContainer variant="brightBlue" size="md">
                <Sparkles className="w-5 h-5" />
              </IconContainer>
              <IconContainer variant="teal" size="md">
                <Calculator className="w-5 h-5" />
              </IconContainer>
              <IconContainer variant="navy" size="md">
                <ShieldCheck className="w-5 h-5" />
              </IconContainer>
            </div>
          </div>

          {/* 3. Transparency & Classification Tiers */}
          <div className="space-y-4">
            <h3 className="text-sm font-bold uppercase tracking-wider text-slate-500">
              3. Data Transparency & Source Tiers (Crucial Principle)
            </h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              <Card tier="policy_source" className="p-4 shadow-sm">
                <StatusBadge variant="policy_source" className="mb-2" />
                <h4 className="text-sm font-bold text-[#0A1D2E]">Tier 1: Policy Source</h4>
                <p className="text-xs text-slate-500 mt-1">
                  Direct text cited from official SBC / plan contract documents.
                </p>
              </Card>

              <Card tier="ai_interpretation" className="p-4 shadow-sm">
                <StatusBadge variant="ai_interpretation" className="mb-2" />
                <h4 className="text-sm font-bold text-[#0A1D2E]">Tier 2: AI Extraction</h4>
                <p className="text-xs text-slate-500 mt-1">
                  Semantic entity recognition identifying deductible and copay rules.
                </p>
              </Card>

              <Card tier="deterministic_calc" className="p-4 shadow-sm">
                <StatusBadge variant="deterministic_calc" className="mb-2" />
                <h4 className="text-sm font-bold text-[#0A1D2E]">Tier 3: Deterministic Math</h4>
                <p className="text-xs text-slate-500 mt-1">
                  Audited calculations with zero hallucinations or probabilistic math.
                </p>
              </Card>

              <Card tier="estimated_result" className="p-4 shadow-sm">
                <StatusBadge variant="estimated" className="mb-2" />
                <h4 className="text-sm font-bold text-[#0A1D2E]">Tier 4: Patient Estimate</h4>
                <p className="text-xs text-slate-500 mt-1">
                  Provisional out-of-pocket guidance (not a guaranteed bill).
                </p>
              </Card>
            </div>
          </div>

          {/* 4. Financial & Numeric Presentation */}
          <div className="space-y-4">
            <h3 className="text-sm font-bold uppercase tracking-wider text-slate-500">
              4. Financial Metrics & Monospace Precision
            </h3>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <MetricCard
                label="Annual In-Network Deductible"
                value="$1,500.00"
                sourceTier="policy_source"
                subtext="Individual plan year limit"
                icon={<Coins className="w-5 h-5" />}
              />
              <MetricCard
                label="Accumulated Spend to Date"
                value="$920.00"
                sourceTier="deterministic_calc"
                subtext="61.3% of deductible satisfied"
                icon={<Receipt className="w-5 h-5" />}
                trend={{ direction: "up", text: "+$120 this month" }}
              />
              <MetricCard
                label="Estimated Co-Payment Due"
                value="$45.00"
                sourceTier="estimated_result"
                subtext="Estimated for Specialist Office Visit"
                highlight
                icon={<Activity className="w-5 h-5 text-[#0052D1]" />}
              />
            </div>
          </div>

          {/* 5. Compound Card Demonstration */}
          <div className="space-y-4">
            <h3 className="text-sm font-bold uppercase tracking-wider text-slate-500">
              5. Compound Card Component Structure
            </h3>
            <Card hoverLift className="max-w-xl">
              <CardHeader>
                <div className="flex items-center justify-between">
                  <CardTitle>Specialist In-Network Consultation</CardTitle>
                  <StatusBadge variant="covered" size="xs" label="Covered Benefit" />
                </div>
                <CardDescription>
                  CPT Code 99214 • Detailed Office Visit
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-2 text-xs text-slate-600">
                <p>
                  No deductible requirement applies to standard in-network specialist consultations. A fixed copayment of $45 is charged at the time of check-in.
                </p>
              </CardContent>
              <CardFooter>
                <span className="text-xs text-slate-500">Schedule of Benefits §1.4</span>
                <Button variant="outline" size="xs">View Clause</Button>
              </CardFooter>
            </Card>
          </div>

          {/* 6. Progress Bars & Calculators */}
          <div className="space-y-4">
            <h3 className="text-sm font-bold uppercase tracking-wider text-slate-500">
              6. Progress & Coverage Indicators
            </h3>
            <div className="p-6 rounded-2xl bg-slate-50 border border-slate-200 space-y-4">
              <ProgressBar
                label="Deductible Progress"
                value={progressVal}
                max={100}
                variant="teal"
                showValue
                valueFormatter={(val) => `$${val * 15} / $1,500`}
              />
              <ProgressBar
                label="Out-of-Pocket Maximum Cap ($6,000.00)"
                value={42}
                max={100}
                variant="gradient"
                showValue
              />
            </div>
          </div>

          {/* 7. States: Loading, Empty, and Error */}
          <div className="space-y-4">
            <h3 className="text-sm font-bold uppercase tracking-wider text-slate-500">
              7. Application States (Loading, Empty, Error)
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <Card className="p-6 flex flex-col justify-center">
                <LoadingState
                  variant="card"
                  message="Analyzing SBC Document..."
                  subtext="Extracting Section 3: Limitations & Exceptions"
                />
              </Card>

              <EmptyState
                compact
                title="No Treatment Selected"
                description="Choose a common procedure or enter a CPT code to calculate expected out-of-pocket costs."
                action={
                  <Button variant="outline" size="sm">
                    Browse Procedures
                  </Button>
                }
              />

              <ErrorState
                variant="banner"
                title="Clause Ambiguity Detected"
                message="Out-of-network facility charges are listed as 'Not Determined' without prior insurer authorization."
                onRetry={() => {}}
                retryLabel="Re-scan SBC"
              />
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
