import React from "react";
import { SectionHeader } from "@/components/ui/SectionHeader";
import { Card, CardContent } from "@/components/ui/Card";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { IconContainer } from "@/components/ui/IconContainer";
import {
  FileText,
  Cpu,
  Calculator,
  PieChart,
  CheckCircle,
} from "lucide-react";

export function WorkflowSection() {
  const steps = [
    {
      step: "01",
      title: "Document Ingestion",
      tier: "policy_source" as const,
      badgeLabel: "Policy Source",
      icon: FileText,
      iconVariant: "primary" as const,
      description:
        "Upload your Summary of Benefits and Coverage (SBC) or policy contract. Multi-layer parsing reads tables and clauses cleanly.",
      highlight: "Raw text & tables indexed",
    },
    {
      step: "02",
      title: "AI Clause Extraction",
      tier: "ai_interpretation" as const,
      badgeLabel: "AI Interpretation",
      icon: Cpu,
      iconVariant: "brightBlue" as const,
      description:
        "Local LLM models isolate key terms: individual deductibles, family caps, co-insurance tiers, and explicit exclusions.",
      highlight: "Verifiable citations preserved",
    },
    {
      step: "03",
      title: "Deterministic Engine",
      tier: "deterministic_calc" as const,
      badgeLabel: "Deterministic Engine",
      icon: Calculator,
      iconVariant: "teal" as const,
      description:
        "No LLM math. A deterministic rules engine runs strict mathematical formulas against contracted allowances and limits.",
      highlight: "Zero calculation hallucination",
    },
    {
      step: "04",
      title: "Patient Cost Estimate",
      tier: "estimated" as const,
      badgeLabel: "Patient Estimate",
      icon: PieChart,
      iconVariant: "amber" as const,
      description:
        "Get transparent estimates of what the insurer pays versus your estimated out-of-pocket obligation before care is received.",
      highlight: "Provisional patient guidance",
    },
  ];

  return (
    <section id="how-it-works" className="py-16 sm:py-24 bg-white">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <SectionHeader
          badge="4-Stage Workflow"
          badgeVariant="teal"
          title="From Complex Policy PDF to Clear Dollar Breakdown"
          description="How CoverWise AI separates probabilistic document understanding from exact mathematical calculations."
          align="center"
        />

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mt-10">
          {steps.map((item) => {
            const Icon = item.icon;
            return (
              <Card
                key={item.step}
                className="relative flex flex-col justify-between border-slate-200/90 hover:border-[#1769FF]/40 hover:shadow-lg transition-all duration-200"
              >
                <CardContent className="p-6 flex flex-col gap-4">
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-2xl font-bold text-slate-300">
                      {item.step}
                    </span>
                    <StatusBadge variant={item.tier} size="xs" label={item.badgeLabel} />
                  </div>

                  <IconContainer variant={item.iconVariant} size="lg" shape="rounded">
                    <Icon className="w-6 h-6" />
                  </IconContainer>

                  <div className="flex flex-col gap-1.5">
                    <h3 className="text-base font-bold text-[#0A1D2E]">
                      {item.title}
                    </h3>
                    <p className="text-xs text-slate-600 leading-relaxed">
                      {item.description}
                    </p>
                  </div>
                </CardContent>

                <div className="px-6 py-3 border-t border-slate-100 bg-slate-50/60 rounded-b-2xl flex items-center gap-2 text-[11px] text-slate-600 font-medium">
                  <CheckCircle className="w-3.5 h-3.5 text-emerald-600 shrink-0" />
                  <span className="truncate">{item.highlight}</span>
                </div>
              </Card>
            );
          })}
        </div>
      </div>
    </section>
  );
}
