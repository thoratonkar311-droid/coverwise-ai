"use client";

import React from "react";
import Link from "next/link";
import { Button } from "@/components/ui/Button";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { HeroIntelligenceVisualization } from "./HeroIntelligenceVisualization";
import {
  FileUp,
  ArrowRight,
  ShieldCheck,
  Calculator,
  Lock,
  Sparkles,
} from "lucide-react";

export function HeroSection() {
  return (
    <section className="relative overflow-hidden pt-8 pb-16 sm:pt-14 sm:pb-24 border-b border-slate-200/60 bg-gradient-to-b from-[#EEF4FF]/50 via-[#F8F9FF] to-white">
      {/* Background soft glow */}
      <div
        className="absolute top-0 left-1/2 -translate-x-1/2 w-full max-w-7xl h-[450px] bg-gradient-to-br from-[#1769FF]/12 via-[#71F8E4]/8 to-transparent blur-3xl pointer-events-none -z-10"
        aria-hidden="true"
      />

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-12 lg:gap-8 items-center">
          {/* Left Column: Heading and Value Proposition */}
          <div className="lg:col-span-6 xl:col-span-7 flex flex-col items-start gap-6">
            {/* Eyebrow / Trust Indicator */}
            <div className="inline-flex items-center gap-2 bg-[#EEF4FF] border border-blue-200/90 px-3.5 py-1.5 rounded-full text-xs font-semibold text-[#0052D1] shadow-xs">
              <Sparkles className="w-3.5 h-3.5 text-[#1769FF]" />
              <span>AI-Powered Coverage Intelligence</span>
              <span className="w-1.5 h-1.5 rounded-full bg-[#1769FF]" />
              <span className="text-slate-600 font-normal">v0.1 Prototype</span>
            </div>

            {/* Main Headline */}
            <h1 className="text-3xl sm:text-5xl xl:text-6xl font-extrabold text-[#0A1D2E] tracking-tight leading-[1.12]">
              From Policy to Patient.{" "}
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-[#0052D1] via-[#1769FF] to-[#006B5F] block sm:inline">
                Know What Your Treatment Will Cost.
              </span>
            </h1>

            {/* Supporting Text */}
            <p className="text-base sm:text-lg text-slate-600 leading-relaxed max-w-2xl">
              CoverWise AI analyzes your insurance policy documents, interprets complex
              clauses, and performs deterministic mathematical calculations to help you
              understand your coverage limits and estimate out-of-pocket treatment costs.
            </p>

            {/* Call To Actions */}
            <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3 w-full sm:w-auto pt-1">
              <Button
                variant="primary"
                size="lg"
                leftIcon={<FileUp className="w-4 h-4" />}
                rightIcon={<ArrowRight className="w-4 h-4" />}
                className="shadow-md shadow-blue-600/20 font-semibold"
              >
                Analyze My Policy
              </Button>
              <Link href="#how-it-works">
                <Button
                  variant="outline"
                  size="lg"
                  className="w-full sm:w-auto bg-white/90 border-slate-300 text-slate-800 hover:text-[#0052D1] hover:bg-[#EEF4FF]"
                >
                  See How It Works
                </Button>
              </Link>
            </div>

            {/* Trust and Feature Indicators (No unsupported certification claims) */}
            <div className="pt-4 border-t border-slate-200/80 w-full flex flex-col gap-3">
              <div className="flex flex-wrap items-center gap-x-6 gap-y-2 text-xs text-slate-600 font-medium">
                <div className="flex items-center gap-2">
                  <Calculator className="w-4 h-4 text-[#006B5F]" />
                  <span>Deterministic Math Engine</span>
                </div>
                <div className="flex items-center gap-2">
                  <ShieldCheck className="w-4 h-4 text-[#0052D1]" />
                  <span>Clause-by-Clause Audit Trail</span>
                </div>
                <div className="flex items-center gap-2">
                  <Lock className="w-4 h-4 text-slate-500" />
                  <span>Local Document Ingestion</span>
                </div>
              </div>

              {/* 4-tier Classification Legend */}
              <div className="pt-2">
                <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block mb-2">
                  Transparency Classification Tiers:
                </span>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs">
                  <StatusBadge variant="policy_source" size="xs" label="1. Policy Source" />
                  <StatusBadge variant="ai_interpretation" size="xs" label="2. AI Extraction" />
                  <StatusBadge variant="deterministic_calc" size="xs" label="3. Exact Math" />
                  <StatusBadge variant="estimated" size="xs" label="4. Patient Estimate" />
                </div>
              </div>
            </div>
          </div>

          {/* Right Column: Hero Intelligence Visualization */}
          <div className="lg:col-span-6 xl:col-span-5 w-full flex justify-center lg:justify-end">
            <HeroIntelligenceVisualization />
          </div>
        </div>
      </div>
    </section>
  );
}
