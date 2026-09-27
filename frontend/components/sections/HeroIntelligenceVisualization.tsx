"use client";

import React from "react";
import {
  FileText,
  ShieldCheck,
  Stethoscope,
  Receipt,
  Coins,
  HeartPulse,
  Sparkles,
} from "lucide-react";
import { Badge } from "@/components/ui/Badge";
import { StatusBadge } from "@/components/ui/StatusBadge";

export function HeroIntelligenceVisualization() {
  const nodes = [
    {
      id: "policy",
      label: "POLICY",
      sub: "SBC Clauses",
      icon: FileText,
      color: "border-blue-400 bg-[#EEF4FF] text-[#0052D1]",
      position: "top-[6%] left-[12%]",
      lineX: "24%",
      lineY: "18%",
    },
    {
      id: "coverage",
      label: "COVERAGE",
      sub: "Limits & Caps",
      icon: ShieldCheck,
      color: "border-teal-400 bg-[#E6F7F5] text-[#006B5F]",
      position: "top-[8%] right-[10%]",
      lineX: "76%",
      lineY: "18%",
    },
    {
      id: "treatment",
      label: "TREATMENT",
      sub: "Clinical Codes",
      icon: Stethoscope,
      color: "border-indigo-400 bg-[#F5F3FF] text-[#5B21B6]",
      position: "bottom-[22%] right-[4%]",
      lineX: "80%",
      lineY: "68%",
    },
    {
      id: "claim",
      label: "CLAIM",
      sub: "Allowed Math",
      icon: Receipt,
      color: "border-slate-400 bg-slate-50 text-slate-700",
      position: "bottom-[24%] left-[4%]",
      lineX: "20%",
      lineY: "68%",
    },
    {
      id: "patient-cost",
      label: "PATIENT COST",
      sub: "Final Estimate",
      icon: Coins,
      color: "border-amber-400 bg-[#FFFBEB] text-[#B45309]",
      position: "bottom-[2%] left-1/2 -translate-x-1/2",
      lineX: "50%",
      lineY: "84%",
    },
  ];

  return (
    <div className="relative w-full max-w-[540px] aspect-square mx-auto flex items-center justify-center select-none overflow-hidden sm:overflow-visible">
      {/* Background radial glow */}
      <div
        className="absolute inset-0 bg-gradient-to-tr from-[#0052D1]/15 via-[#71F8E4]/15 to-transparent rounded-full blur-3xl pointer-events-none animate-pulse-glow"
        aria-hidden="true"
      />

      {/* SVG Connecting Data-Bus Lines */}
      <svg
        className="absolute inset-0 w-full h-full pointer-events-none z-0"
        viewBox="0 0 100 100"
        preserveAspectRatio="none"
        aria-hidden="true"
      >
        <defs>
          <linearGradient id="busGradBlue" x1="50%" y1="50%" x2="24%" y2="18%">
            <stop offset="0%" stopColor="#1769FF" stopOpacity="0.8" />
            <stop offset="100%" stopColor="#0052D1" stopOpacity="0.2" />
          </linearGradient>
          <linearGradient id="busGradTeal" x1="50%" y1="50%" x2="76%" y2="18%">
            <stop offset="0%" stopColor="#71F8E4" stopOpacity="0.8" />
            <stop offset="100%" stopColor="#006B5F" stopOpacity="0.2" />
          </linearGradient>
          <linearGradient id="busGradPurple" x1="50%" y1="50%" x2="80%" y2="68%">
            <stop offset="0%" stopColor="#1769FF" stopOpacity="0.8" />
            <stop offset="100%" stopColor="#5B21B6" stopOpacity="0.2" />
          </linearGradient>
          <linearGradient id="busGradSlate" x1="50%" y1="50%" x2="20%" y2="68%">
            <stop offset="0%" stopColor="#0052D1" stopOpacity="0.8" />
            <stop offset="100%" stopColor="#64748B" stopOpacity="0.2" />
          </linearGradient>
          <linearGradient id="busGradAmber" x1="50%" y1="50%" x2="50%" y2="84%">
            <stop offset="0%" stopColor="#006B5F" stopOpacity="0.8" />
            <stop offset="100%" stopColor="#D97706" stopOpacity="0.2" />
          </linearGradient>
        </defs>

        {/* Lines from Center (50, 50) to Satellite Nodes */}
        <line x1="50" y1="50" x2="24" y2="18" stroke="url(#busGradBlue)" strokeWidth="0.75" strokeDasharray="2 2" />
        <line x1="50" y1="50" x2="76" y2="18" stroke="url(#busGradTeal)" strokeWidth="0.75" strokeDasharray="2 2" />
        <line x1="50" y1="50" x2="80" y2="68" stroke="url(#busGradPurple)" strokeWidth="0.75" strokeDasharray="2 2" />
        <line x1="50" y1="50" x2="20" y2="68" stroke="url(#busGradSlate)" strokeWidth="0.75" strokeDasharray="2 2" />
        <line x1="50" y1="50" x2="50" y2="84" stroke="url(#busGradAmber)" strokeWidth="0.75" strokeDasharray="2 2" />
      </svg>

      {/* Orbit Rings */}
      <div className="absolute w-[86%] h-[86%] rounded-full border border-slate-200/60 pointer-events-none animate-spin-orbit" />
      <div className="absolute w-[70%] h-[70%] rounded-full border border-dashed border-[#1769FF]/20 pointer-events-none animate-spin-orbit-rev" />
      <div className="absolute w-[50%] h-[50%] rounded-full border border-teal-200/40 pointer-events-none" />

      {/* Ambient Floating Particle Dots */}
      <div className="absolute top-[28%] left-[22%] w-2 h-2 rounded-full bg-[#1769FF]/40 animate-pulse" />
      <div className="absolute top-[32%] right-[24%] w-2.5 h-2.5 rounded-full bg-[#71F8E4]/60 animate-pulse" />
      <div className="absolute bottom-[35%] left-[28%] w-2 h-2 rounded-full bg-indigo-400/40 animate-pulse" />
      <div className="absolute bottom-[28%] right-[25%] w-2 h-2 rounded-full bg-amber-400/40 animate-pulse" />

      {/* Surrounding Conceptual Satellite Nodes */}
      {nodes.map((node) => {
        const Icon = node.icon;
        return (
          <div
            key={node.id}
            className={`absolute ${node.position} z-10 flex flex-col items-center gap-1 group transition-transform duration-200 hover:scale-105`}
          >
            <div
              className={`w-9 h-9 sm:w-11 sm:h-11 rounded-2xl border ${node.color} flex items-center justify-center shadow-sm group-hover:shadow-md transition-shadow`}
            >
              <Icon className="w-4 h-4 sm:w-5 sm:h-5" />
            </div>
            <div className="text-center px-1.5 py-0.5 rounded-md bg-white/90 backdrop-blur-sm border border-slate-100 shadow-[0_1px_3px_rgba(0,0,0,0.04)]">
              <span className="block text-[9px] sm:text-[10px] font-bold tracking-wider text-slate-800 uppercase">
                {node.label}
              </span>
              <span className="block text-[8px] sm:text-[9px] text-slate-500 font-medium">
                {node.sub}
              </span>
            </div>
          </div>
        );
      })}

      {/* Central Health / Intelligence CORE Element */}
      <div className="relative z-20 flex flex-col items-center justify-center">
        {/* Pulsing ring aura */}
        <div className="w-24 h-24 sm:w-28 sm:h-28 rounded-full bg-gradient-to-tr from-[#0052D1] via-[#1769FF] to-[#006B5F] p-1 shadow-[0_0_35px_rgba(23,105,255,0.35)] flex items-center justify-center">
          <div className="w-full h-full rounded-full bg-[#0A1D2E] flex flex-col items-center justify-center text-white p-2 text-center border border-white/20">
            <HeartPulse className="w-7 h-7 sm:w-8 sm:h-8 text-[#71F8E4] stroke-[2.2] animate-pulse" />
            <span className="text-[10px] font-extrabold tracking-widest uppercase text-white mt-1">
              CORE
            </span>
          </div>
        </div>
        <div className="mt-2 text-center">
          <span className="inline-flex items-center gap-1 text-[10px] font-semibold text-[#0052D1] bg-[#EEF4FF] px-2 py-0.5 rounded-full border border-blue-200">
            <Sparkles className="w-2.5 h-2.5 text-[#1769FF]" />
            Deterministic Engine
          </span>
        </div>
      </div>

      {/* Floating Demo Metric Cards (Glassmorphism & Monospace Numbers) */}

      {/* Metric 1: Policy Coverage: 82% (Top-Left) */}
      <div className="absolute top-[2%] left-[2%] sm:left-[0%] z-30 animate-float-slow">
        <div className="bg-white/95 backdrop-blur-md border border-slate-200/90 rounded-xl p-2.5 sm:p-3 shadow-lg max-w-[155px] sm:max-w-[175px]">
          <div className="flex items-center justify-between gap-1 mb-1">
            <span className="text-[10px] sm:text-[11px] font-medium text-slate-500 truncate">
              Policy Coverage
            </span>
            <Badge variant="teal" size="xs">
              Demo
            </Badge>
          </div>
          <div className="font-mono text-base sm:text-lg font-bold text-[#006B5F] tracking-tight">
            82%
          </div>
          <span className="text-[9px] text-slate-400 block truncate">
            In-Network Benefit Tier
          </span>
        </div>
      </div>

      {/* Metric 2: Total Est. Treatment: ₹2,60,000 (Top-Right) */}
      <div className="absolute top-[4%] right-[0%] sm:right-[-2%] z-30 animate-float-reverse">
        <div className="bg-white/95 backdrop-blur-md border border-slate-200/90 rounded-xl p-2.5 sm:p-3 shadow-lg max-w-[165px] sm:max-w-[185px]">
          <div className="flex items-center justify-between gap-1 mb-1">
            <span className="text-[10px] sm:text-[11px] font-medium text-slate-500 truncate">
              Total Est. Treatment
            </span>
            <Badge variant="default" size="xs">
              Example
            </Badge>
          </div>
          <div className="font-mono text-base sm:text-lg font-bold text-[#0A1D2E] tracking-tight">
            ₹2,60,000
          </div>
          <span className="text-[9px] text-slate-400 block truncate">
            Hospital Quotation
          </span>
        </div>
      </div>

      {/* Metric 3: Insurance Pays: 85.2% • ₹2,21,500 (Bottom-Left) */}
      <div className="absolute bottom-[8%] left-[0%] sm:left-[-3%] z-30 animate-float-reverse">
        <div className="bg-[#E6F7F5]/95 backdrop-blur-md border border-teal-200/90 rounded-xl p-2.5 sm:p-3 shadow-lg max-w-[170px] sm:max-w-[190px]">
          <div className="flex items-center justify-between gap-1 mb-0.5">
            <span className="text-[10px] sm:text-[11px] font-semibold text-[#006B5F]">
              Insurance Pays
            </span>
            <StatusBadge variant="deterministic_calc" size="xs" label="Math" />
          </div>
          <div className="font-mono text-sm sm:text-base font-bold text-[#006B5F]">
            ₹2,21,500
          </div>
          <span className="text-[9px] font-mono text-teal-700 block">
            85.2% Covered Share (Demo)
          </span>
        </div>
      </div>

      {/* Metric 4: Patient Liability: ₹38,500 (Bottom-Right) */}
      <div className="absolute bottom-[6%] right-[0%] sm:right-[-2%] z-30 animate-float-slow">
        <div className="bg-[#FFFBEB]/95 backdrop-blur-md border border-amber-300 rounded-xl p-2.5 sm:p-3 shadow-lg max-w-[165px] sm:max-w-[185px] ring-2 ring-amber-400/20">
          <div className="flex items-center justify-between gap-1 mb-0.5">
            <span className="text-[10px] sm:text-[11px] font-semibold text-[#92400E]">
              Patient Liability
            </span>
            <StatusBadge variant="estimated" size="xs" label="Provisional" />
          </div>
          <div className="font-mono text-base sm:text-lg font-bold text-[#B45309]">
            ₹38,500
          </div>
          <span className="text-[9px] text-amber-700 block">
            Patient Estimate (Demo)
          </span>
        </div>
      </div>
    </div>
  );
}
