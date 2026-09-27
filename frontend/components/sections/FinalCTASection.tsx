import React from "react";
import Link from "next/link";
import { Button } from "@/components/ui/Button";
import {
  FileUp,
  ArrowRight,
  ShieldCheck,
  Calculator,
  Lock,
  Info,
} from "lucide-react";

export function FinalCTASection() {
  return (
    <section className="relative overflow-hidden py-16 sm:py-24 bg-[#0A1D2E] text-white">
      {/* Background glow effects */}
      <div
        className="absolute top-0 right-1/4 w-96 h-96 bg-[#1769FF]/20 rounded-full blur-3xl pointer-events-none"
        aria-hidden="true"
      />
      <div
        className="absolute bottom-0 left-1/4 w-96 h-96 bg-[#71F8E4]/15 rounded-full blur-3xl pointer-events-none"
        aria-hidden="true"
      />

      <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10 text-center">
        <div className="inline-flex items-center gap-2 bg-white/10 backdrop-blur-md border border-white/20 px-3.5 py-1.5 rounded-full text-xs font-semibold text-[#71F8E4] mb-6">
          <ShieldCheck className="w-3.5 h-3.5 text-[#71F8E4]" />
          <span>Patient-Centric Health Insurance Intelligence</span>
        </div>

        <h2 className="text-3xl sm:text-4xl lg:text-5xl font-extrabold tracking-tight text-white leading-tight">
          Ready to understand your coverage{" "}
          <span className="text-transparent bg-clip-text bg-gradient-to-r from-[#71F8E4] via-blue-400 to-[#1769FF]">
            before you receive care?
          </span>
        </h2>

        <p className="mt-4 text-base sm:text-lg text-slate-300 max-w-2xl mx-auto leading-relaxed">
          Upload your insurance policy document to extract deductible status, coinsurance
          rates, and calculate patient responsibility with auditable clause citations.
        </p>

        {/* CTA Buttons */}
        <div className="mt-8 flex flex-col sm:flex-row items-center justify-center gap-4">
          <Button
            variant="primary"
            size="lg"
            leftIcon={<FileUp className="w-4 h-4" />}
            rightIcon={<ArrowRight className="w-4 h-4" />}
            className="w-full sm:w-auto shadow-lg shadow-blue-500/30 font-semibold"
          >
            Analyze My Policy
          </Button>

          <Link href="#coverage-intelligence" className="w-full sm:w-auto">
            <Button
              variant="outline"
              size="lg"
              className="w-full sm:w-auto border-white/30 text-white hover:bg-white/10 hover:text-white"
            >
              Explore Sample Scenario
            </Button>
          </Link>
        </div>

        {/* Feature Pills */}
        <div className="mt-10 pt-8 border-t border-white/10 flex flex-wrap justify-center items-center gap-6 text-xs text-slate-400">
          <div className="flex items-center gap-2">
            <Calculator className="w-4 h-4 text-[#71F8E4]" />
            <span>Deterministic Math (No LLM Calculation Errors)</span>
          </div>
          <div className="flex items-center gap-2">
            <ShieldCheck className="w-4 h-4 text-blue-400" />
            <span>Verifiable Policy Source Citations</span>
          </div>
          <div className="flex items-center gap-2">
            <Lock className="w-4 h-4 text-teal-300" />
            <span>Private & Educational Prototype</span>
          </div>
        </div>

        {/* Mandatory Disclaimer */}
        <div className="mt-8 p-4 rounded-2xl bg-white/5 border border-white/10 max-w-3xl mx-auto text-left flex items-start gap-3">
          <Info className="w-4 h-4 text-[#71F8E4] shrink-0 mt-0.5" />
          <p className="text-xs text-slate-300 leading-relaxed">
            <strong className="text-white font-semibold">Important Disclaimer:</strong> CoverWise
            AI provides informational estimates based on available policy information and
            user-provided treatment costs. It does not provide insurer authorization or guarantee claim
            payment.
          </p>
        </div>
      </div>
    </section>
  );
}
