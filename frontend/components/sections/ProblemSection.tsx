import React from "react";
import { SectionHeader } from "@/components/ui/SectionHeader";
import { Card, CardContent } from "@/components/ui/Card";
import { IconContainer } from "@/components/ui/IconContainer";
import { Badge } from "@/components/ui/Badge";
import {
  FileSpreadsheet,
  Hospital,
  AlertTriangle,
  Clock,
} from "lucide-react";

export function ProblemSection() {
  const problems = [
    {
      id: "complex-policies",
      title: "Complex Policies",
      icon: FileSpreadsheet,
      iconVariant: "primary" as const,
      accentBorder: "border-t-4 border-t-[#0052D1]",
      description:
        "Insurance policies contain dense clauses, exclusions, sub-limits, deductibles, room-rent capping conditions, and disease-specific waiting periods that are overwhelming to navigate.",
      demoStat: "40+ Pages of Legal Terms",
      demoStatSub: "Average health policy schedule",
      clauses: ["Room Rent Sub-limits", "Pre-existing Waiting Periods", "Proportionate Deductions"],
    },
    {
      id: "unclear-costs",
      title: "Unclear Treatment Costs",
      icon: Hospital,
      iconVariant: "brightBlue" as const,
      accentBorder: "border-t-4 border-t-[#1769FF]",
      description:
        "Patients frequently receive preliminary hospital estimates without understanding how insurance network allowances and contracted rates may alter their actual financial liability.",
      demoStat: "Variable Tariff Schedules",
      demoStatSub: "In-network vs out-of-network rates",
      clauses: ["Allowed Tariff Rates", "Implant Capping", "Ancillary Facility Charges"],
    },
    {
      id: "unexpected-out-of-pocket",
      title: "Unexpected Out-of-Pocket",
      icon: AlertTriangle,
      iconVariant: "amber" as const,
      accentBorder: "border-t-4 border-t-[#D97706]",
      description:
        "Deductibles, coinsurance tiers, non-payable consumable items, and policy limits frequently result in surprise out-of-pocket bills despite having comprehensive coverage.",
      demoStat: "15% – 35% Bill Disallowance",
      demoStatSub: "Typical non-medical consumable gap (Demo)",
      clauses: ["Non-Payable Consumables", "Mandatory Copayments", "Deductible Balance"],
    },
  ];

  return (
    <section id="product" className="py-16 sm:py-24 bg-white border-b border-slate-200/60">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <SectionHeader
          badge="The Coverage Clarity Gap"
          badgeVariant="primary"
          title="Insurance shouldn't feel impossible to understand."
          description="Patients shouldn't have to wait until discharge day to discover what their insurance covers. CoverWise AI breaks down the opacity in modern healthcare financing."
          align="center"
        />

        <div className="grid grid-cols-1 md:grid-cols-3 gap-8 mt-12">
          {problems.map((item) => {
            const Icon = item.icon;
            return (
              <Card
                key={item.id}
                className={`relative flex flex-col justify-between ${item.accentBorder} shadow-[0_2px_12px_rgba(10,29,46,0.04)] hover:shadow-xl transition-all duration-300 group`}
              >
                <CardContent className="p-6 sm:p-8 flex flex-col gap-5">
                  <div className="flex items-center justify-between">
                    <IconContainer variant={item.iconVariant} size="lg" shape="rounded">
                      <Icon className="w-6 h-6" />
                    </IconContainer>
                    <Badge variant="subtle" size="xs">
                      Demo Context
                    </Badge>
                  </div>

                  <div className="flex flex-col gap-2">
                    <h3 className="text-xl font-bold text-[#0A1D2E] tracking-tight group-hover:text-[#0052D1] transition-colors">
                      {item.title}
                    </h3>
                    <p className="text-xs sm:text-sm text-slate-600 leading-relaxed">
                      {item.description}
                    </p>
                  </div>

                  {/* Demo Metric Highlight */}
                  <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-100 flex flex-col gap-0.5">
                    <span className="font-mono text-sm font-bold text-[#0A1D2E]">
                      {item.demoStat}
                    </span>
                    <span className="text-[11px] text-slate-500">
                      {item.demoStatSub}
                    </span>
                  </div>

                  {/* Key clauses tags */}
                  <div className="pt-2 flex flex-col gap-1.5">
                    <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                      Affected Policy Terms:
                    </span>
                    <div className="flex flex-wrap gap-1.5">
                      {item.clauses.map((clause) => (
                        <span
                          key={clause}
                          className="text-[11px] px-2 py-0.5 rounded-md bg-[#EEF4FF] text-[#0052D1] font-medium"
                        >
                          {clause}
                        </span>
                      ))}
                    </div>
                  </div>
                </CardContent>

                <div className="px-6 py-3 border-t border-slate-100 bg-slate-50/50 rounded-b-2xl flex items-center justify-between text-xs text-slate-500">
                  <span className="flex items-center gap-1.5">
                    <Clock className="w-3.5 h-3.5 text-slate-400" />
                    <span>Deterministic Clarity</span>
                  </span>
                  <span className="font-mono text-[11px] text-emerald-700 font-semibold">
                    Audited Engine
                  </span>
                </div>
              </Card>
            );
          })}
        </div>
      </div>
    </section>
  );
}
