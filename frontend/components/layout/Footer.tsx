import React from "react";
import Link from "next/link";
import { ShieldCheck, Info } from "lucide-react";

export function Footer() {
  return (
    <footer id="about" className="mt-auto border-t border-slate-200 bg-white">
      {/* Disclaimer Banner */}
      <div className="bg-[#EEF4FF] border-b border-blue-100 py-3.5 px-4 sm:px-6">
        <div className="max-w-7xl mx-auto flex items-start sm:items-center gap-2.5 text-xs text-[#0043AA]">
          <Info className="w-4 h-4 shrink-0 text-[#0052D1] mt-0.5 sm:mt-0" />
          <p className="leading-relaxed">
            <strong className="font-semibold">Patient Notice & Transparency:</strong> CoverWise AI
            provides informational estimates based on available policy information and user-provided
            treatment costs. It does not provide insurer authorization or guarantee claim payment.
          </p>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10 sm:py-12">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
          <div className="md:col-span-2 flex flex-col gap-3">
            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 rounded-lg bg-[#0052D1] flex items-center justify-center text-white">
                <ShieldCheck className="w-5 h-5" />
              </div>
              <span className="text-base font-bold text-[#0A1D2E]">CoverWise AI</span>
            </div>
            <p className="text-xs text-slate-500 max-w-sm leading-relaxed">
              Policy-to-Patient intelligence bridging complex insurance fine print,
              deterministic deductible calculations, and treatment out-of-pocket estimates.
            </p>
            <div className="flex items-center gap-2 text-[11px] font-mono text-slate-400 mt-2">
              <span className="w-2 h-2 rounded-full bg-emerald-500 inline-block" />
              <span>Deterministic Rules Engine v0.1 • Local AI Pipeline</span>
            </div>
          </div>

          <div className="flex flex-col gap-2.5 text-xs">
            <span className="font-semibold text-[#0A1D2E] tracking-tight uppercase text-[11px]">
              Platform Intelligence
            </span>
            <Link href="#product" className="text-slate-600 hover:text-[#0052D1] transition-colors">
              Policy Ingestion & OCR
            </Link>
            <Link href="#how-it-works" className="text-slate-600 hover:text-[#0052D1] transition-colors">
              Deterministic Rules Engine
            </Link>
            <Link href="#coverage-intelligence" className="text-slate-600 hover:text-[#0052D1] transition-colors">
              Coverage Intelligence
            </Link>
            <Link href="#treatment-costs" className="text-slate-600 hover:text-[#0052D1] transition-colors">
              Treatment Cost Estimator
            </Link>
          </div>

          <div className="flex flex-col gap-2.5 text-xs">
            <span className="font-semibold text-[#0A1D2E] tracking-tight uppercase text-[11px]">
              Transparency & Tiers
            </span>
            <div className="flex items-center gap-1.5 text-slate-600">
              <span className="w-2 h-2 rounded-full bg-[#0052D1]" />
              <span>Policy Source Documentation</span>
            </div>
            <div className="flex items-center gap-1.5 text-slate-600">
              <span className="w-2 h-2 rounded-full bg-[#6366F1]" />
              <span>AI Clause Interpretation</span>
            </div>
            <div className="flex items-center gap-1.5 text-slate-600">
              <span className="w-2 h-2 rounded-full bg-[#006B5F]" />
              <span>Deterministic Calculation</span>
            </div>
            <div className="flex items-center gap-1.5 text-slate-600">
              <span className="w-2 h-2 rounded-full bg-[#D97706]" />
              <span>Patient Responsibility Estimate</span>
            </div>
          </div>
        </div>

        <div className="mt-8 pt-6 border-t border-slate-100 flex flex-col sm:flex-row items-center justify-between gap-4 text-xs text-slate-400">
          <p>© {new Date().getFullYear()} CoverWise AI. Educational and Patient Decision Support Prototype.</p>
          <div className="flex items-center gap-4">
            <span className="hover:text-slate-600 cursor-pointer">Privacy Framework</span>
            <span className="hover:text-slate-600 cursor-pointer">Terms of Service</span>
            <span className="hover:text-slate-600 cursor-pointer">Patient Privacy Guidelines</span>
          </div>
        </div>
      </div>
    </footer>
  );
}
