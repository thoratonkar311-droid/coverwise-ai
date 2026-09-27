import React from "react";
import { SectionHeader } from "@/components/ui/SectionHeader";
import { Card, CardContent } from "@/components/ui/Card";
import { IconContainer } from "@/components/ui/IconContainer";
import { StatusBadge } from "@/components/ui/StatusBadge";
import {
  FileUp,
  FileSearch,
  Stethoscope,
  Calculator,
  Coins,
  CheckCircle2,
} from "lucide-react";

export function HowItWorksSection() {
  const steps = [
    {
      step: "01",
      title: "Upload Policy",
      tier: "policy_source" as const,
      tierLabel: "Policy Source",
      icon: FileUp,
      iconVariant: "primary" as const,
      description:
        "Upload your Summary of Benefits & Coverage (SBC) or policy schedule. The ingestion pipeline extracts tables and clauses cleanly.",
      detail: "Supports PDF & scanned schedules",
    },
    {
      step: "02",
      title: "Understand Coverage",
      tier: "ai_interpretation" as const,
      tierLabel: "AI Extraction",
      icon: FileSearch,
      iconVariant: "brightBlue" as const,
      description:
        "AI models parse and index deductibles, room rent limits, copayment tiers, and exclusions with verifiable page citations.",
      detail: "Auditable clause references",
    },
    {
      step: "03",
      title: "Select Treatment",
      tier: "policy_source" as const,
      tierLabel: "Procedure Input",
      icon: Stethoscope,
      iconVariant: "teal" as const,
      description:
        "Select your planned procedure or diagnostic scan, or enter preliminary estimates from a hospital quotation.",
      detail: "CPT & clinical category mapping",
    },
    {
      step: "04",
      title: "Apply Coverage Rules",
      tier: "deterministic_calc" as const,
      tierLabel: "Deterministic Math",
      icon: Calculator,
      iconVariant: "navy" as const,
      description:
        "The deterministic rules engine computes exact contracted allowances, remaining deductibles, and coinsurance math.",
      detail: "Zero hallucination guarantee",
    },
    {
      step: "05",
      title: "Estimate Patient Cost",
      tier: "estimated" as const,
      tierLabel: "Patient Estimate",
      icon: Coins,
      iconVariant: "amber" as const,
      description:
        "Receive a clear breakdown of estimated insurer responsibility versus your estimated out-of-pocket patient liability.",
      detail: "Clear provisional estimate",
    },
  ];

  return (
    <section id="how-it-works" className="py-16 sm:py-24 bg-[#F8F9FF] border-b border-slate-200/60">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <SectionHeader
          badge="Five-Step Workflow"
          badgeVariant="teal"
          title="How CoverWise AI Delivers Clarity"
          description="A transparent, five-stage pipeline designed to separate AI clause extraction from exact mathematical calculation."
          align="center"
        />

        {/* Desktop Connecting Progress Track */}
        <div className="hidden lg:block relative my-10">
          <div
            className="absolute top-1/2 left-10 right-10 h-0.5 bg-gradient-to-r from-[#0052D1] via-[#1769FF] to-[#006B5F] -translate-y-1/2 z-0"
            aria-hidden="true"
          />
          <div className="relative z-10 flex justify-between">
            {steps.map((item) => (
              <div
                key={item.step}
                className="w-10 h-10 rounded-full bg-white border-2 border-[#1769FF] shadow-sm flex items-center justify-center font-mono font-bold text-xs text-[#0052D1]"
              >
                {item.step}
              </div>
            ))}
          </div>
        </div>

        {/* 5-Step Cards Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-5 gap-5 mt-8">
          {steps.map((item) => {
            const Icon = item.icon;
            return (
              <Card
                key={item.step}
                className="flex flex-col justify-between border-slate-200 hover:border-[#1769FF]/50 hover:shadow-lg transition-all duration-200 group bg-white"
              >
                <CardContent className="p-5 flex flex-col gap-3.5">
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-xl font-bold text-slate-300 group-hover:text-[#1769FF] transition-colors">
                      {item.step}
                    </span>
                    <StatusBadge variant={item.tier} size="xs" label={item.tierLabel} />
                  </div>

                  <IconContainer variant={item.iconVariant} size="md" shape="rounded">
                    <Icon className="w-5 h-5" />
                  </IconContainer>

                  <div className="flex flex-col gap-1">
                    <h3 className="text-sm font-bold text-[#0A1D2E] group-hover:text-[#0052D1] transition-colors">
                      {item.title}
                    </h3>
                    <p className="text-xs text-slate-600 leading-relaxed">
                      {item.description}
                    </p>
                  </div>
                </CardContent>

                <div className="px-5 py-2.5 border-t border-slate-100 bg-slate-50/70 rounded-b-2xl flex items-center gap-1.5 text-[11px] text-slate-500 font-medium">
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 shrink-0" />
                  <span className="truncate">{item.detail}</span>
                </div>
              </Card>
            );
          })}
        </div>
      </div>
    </section>
  );
}
