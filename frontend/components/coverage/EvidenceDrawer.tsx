"use client";

import React, { useEffect } from "react";
import { EvidenceItem } from "@/types";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import {
  X,
  FileText,
  Sparkles,
  Calculator,
  FileCheck2,
  ChevronRight,
  Info,
} from "lucide-react";

export interface EvidenceDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  evidence: EvidenceItem | null;
  allEvidence?: EvidenceItem[];
  onSelectEvidence?: (item: EvidenceItem) => void;
}

export function EvidenceDrawer({
  isOpen,
  onClose,
  evidence,
  allEvidence,
  onSelectEvidence,
}: EvidenceDrawerProps) {
  // Close on Escape key
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    if (isOpen) {
      window.addEventListener("keydown", handleKeyDown);
      document.body.style.overflow = "hidden";
    }
    return () => {
      window.removeEventListener("keydown", handleKeyDown);
      document.body.style.overflow = "unset";
    };
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const current = evidence || (allEvidence && allEvidence[0]) || null;

  return (
    <div
      className="fixed inset-0 z-50 overflow-hidden"
      role="dialog"
      aria-modal="true"
      aria-labelledby="evidence-drawer-title"
    >
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-slate-900/50 backdrop-blur-xs transition-opacity animate-in fade-in duration-200"
        onClick={onClose}
        aria-hidden="true"
      />

      <div className="fixed inset-y-0 right-0 max-w-full flex pl-0 sm:pl-10">
        {/* Drawer container: Bottom Sheet on Mobile (< sm), Right Drawer on Desktop (sm+) */}
        <div className="w-screen max-w-xl h-full flex flex-col bg-white shadow-2xl overflow-y-auto animate-in slide-in-from-bottom sm:slide-in-from-right duration-300">
          {/* Header */}
          <div className="sticky top-0 z-10 px-6 py-4 bg-white/95 backdrop-blur-md border-b border-slate-100 flex items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-xl bg-[#EEF4FF] text-[#0052D1] flex items-center justify-center font-bold">
                <FileCheck2 className="w-5 h-5" />
              </div>
              <div>
                <h2
                  id="evidence-drawer-title"
                  className="text-base font-bold text-[#0A1D2E] tracking-tight leading-snug"
                >
                  Policy Clause Evidence & Audit
                </h2>
                <p className="text-xs text-slate-500">
                  Verifiable document source and deterministic rule tracing
                </p>
              </div>
            </div>

            <button
              onClick={onClose}
              className="w-8 h-8 rounded-lg text-slate-500 hover:text-slate-800 hover:bg-slate-100 flex items-center justify-center transition-colors cursor-pointer"
              aria-label="Close evidence drawer"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Drawer Body Content */}
          <div className="p-6 space-y-6 flex-1">
            {/* Disclaimer Alert */}
            <div className="p-3.5 rounded-xl bg-[#FFFBEB] border border-amber-200 text-xs text-[#92400E] flex items-start gap-2.5">
              <Info className="w-4 h-4 shrink-0 text-amber-600 mt-0.5" />
              <p className="leading-relaxed">
                <strong>Notice of Interpretation:</strong> CoverWise AI provides informational estimates based
                on available policy information and user-provided treatment costs. It does not provide insurer
                authorization or guarantee claim payment.
              </p>
            </div>

            {/* Evidence Selector if multiple */}
            {allEvidence && allEvidence.length > 1 && (
              <div className="space-y-2">
                <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">
                  Select Evidence Clause ({allEvidence.length}):
                </span>
                <div className="flex flex-col gap-1.5">
                  {allEvidence.map((item) => {
                    const isSelected = current?.id === item.id;
                    return (
                      <button
                        key={item.id}
                        onClick={() => onSelectEvidence && onSelectEvidence(item)}
                        className={`text-left p-2.5 rounded-xl border text-xs transition-all flex items-center justify-between cursor-pointer ${
                          isSelected
                            ? "bg-[#EEF4FF] border-[#1769FF] text-[#0052D1] font-semibold"
                            : "bg-slate-50 border-slate-200 hover:bg-slate-100 text-slate-700"
                        }`}
                      >
                        <span className="truncate pr-2">{item.title}</span>
                        <ChevronRight className="w-3.5 h-3.5 shrink-0 opacity-70" />
                      </button>
                    );
                  })}
                </div>
              </div>
            )}

            {current ? (
              <div className="space-y-5">
                {/* Meta details strip */}
                <div className="p-4 rounded-xl bg-slate-50 border border-slate-200/80 space-y-2.5 text-xs">
                  <div className="flex justify-between items-center pb-2 border-b border-slate-200/60">
                    <span className="text-slate-500">Clause Reference:</span>
                    <span className="font-semibold text-slate-800">{current.clauseReference}</span>
                  </div>
                  <div className="flex justify-between items-center pb-2 border-b border-slate-200/60">
                    <span className="text-slate-500">Document Source:</span>
                    <span className="font-mono text-slate-800">{current.sourceDoc}</span>
                  </div>
                  <div className="flex justify-between items-center pb-2 border-b border-slate-200/60">
                    <span className="text-slate-500">Location:</span>
                    <span className="font-medium text-slate-800">{current.pageNumber}</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-slate-500">AI Extraction Confidence:</span>
                    <span className="font-mono font-bold text-emerald-700">
                      {current.confidence}%
                    </span>
                  </div>
                </div>

                {/* Section 1: SOURCE (What the policy document says) */}
                <div className="rounded-2xl border border-blue-200 bg-[#EEF4FF]/40 p-5 space-y-2.5">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <FileText className="w-4 h-4 text-[#0052D1]" />
                      <span className="text-xs font-bold uppercase tracking-wider text-[#0052D1]">
                        1. SOURCE (Policy Document Verbatim)
                      </span>
                    </div>
                    <Badge variant="default" size="xs">
                      Official Document
                    </Badge>
                  </div>
                  <p className="text-xs text-slate-500">
                    Exact text extracted from the uploaded policy contract without alterations:
                  </p>
                  <blockquote className="p-3.5 rounded-xl bg-white border border-blue-200/70 text-xs sm:text-sm text-slate-800 italic leading-relaxed shadow-2xs">
                    “{current.sourceText}”
                  </blockquote>
                </div>

                {/* Section 2: AI INTERPRETATION (How the extracted clause was interpreted) */}
                <div className="rounded-2xl border border-purple-200 bg-[#F5F3FF]/40 p-5 space-y-2.5">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <Sparkles className="w-4 h-4 text-[#6B21A8]" />
                      <span className="text-xs font-bold uppercase tracking-wider text-[#6B21A8]">
                        2. AI INTERPRETATION
                      </span>
                    </div>
                    <Badge variant="outline" size="xs" className="border-purple-300 text-purple-800">
                      Semantic Classifier
                    </Badge>
                  </div>
                  <p className="text-xs text-slate-500">
                    How the local language model interpreted the clause rules and conditions:
                  </p>
                  <div className="p-3.5 rounded-xl bg-white border border-purple-200/70 text-xs sm:text-sm text-slate-800 leading-relaxed shadow-2xs">
                    {current.aiInterpretation}
                  </div>
                </div>

                {/* Section 3: DETERMINISTIC CALCULATION (How the rule affects the estimate) */}
                <div className="rounded-2xl border border-emerald-200 bg-[#E6F7F5]/40 p-5 space-y-2.5">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <Calculator className="w-4 h-4 text-[#006B5F]" />
                      <span className="text-xs font-bold uppercase tracking-wider text-[#006B5F]">
                        3. DETERMINISTIC CALCULATION
                      </span>
                    </div>
                    <Badge variant="teal" size="xs">
                      Exact Math Formula
                    </Badge>
                  </div>
                  <p className="text-xs text-slate-500">
                    Audited mathematical calculation applied by the deterministic rule engine:
                  </p>
                  <div className="p-3.5 rounded-xl bg-white border border-emerald-200/70 text-xs sm:text-sm font-mono text-slate-800 leading-relaxed shadow-2xs">
                    {current.deterministicRule}
                  </div>
                </div>

                {/* Calculation Impact Summary Box */}
                <div className="p-4 rounded-xl bg-[#0A1D2E] text-white flex flex-col gap-1">
                  <span className="text-[10px] font-bold uppercase tracking-widest text-[#71F8E4]">
                    Calculation Impact Summary
                  </span>
                  <p className="text-xs text-slate-200 leading-relaxed font-sans">
                    {current.calculationImpact}
                  </p>
                </div>
              </div>
            ) : (
              <div className="text-center py-12 text-slate-500 text-xs">
                No clause evidence selected.
              </div>
            )}
          </div>

          {/* Footer */}
          <div className="sticky bottom-0 px-6 py-4 bg-slate-50 border-t border-slate-200 flex items-center justify-between">
            <span className="text-xs text-slate-500">
              Audit ID: <code className="font-mono">{current?.id || "N/A"}</code>
            </span>
            <Button variant="primary" size="sm" onClick={onClose}>
              Done Reviewing
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
