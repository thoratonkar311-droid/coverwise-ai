"use client";

import React, { useState, useRef } from "react";
import Link from "next/link";
import { Header } from "@/components/layout/Header";
import { Footer } from "@/components/layout/Footer";
import { SectionHeader } from "@/components/ui/SectionHeader";
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { ProgressBar } from "@/components/ui/ProgressBar";
import { ErrorState } from "@/components/ui/ErrorState";
import { api, parseApiError } from "@/lib/api";
import { PolicySummary, ApiError } from "@/types";
import { formatCurrency, displayValueOrNotDetermined } from "@/lib/utils";
import {
  FileUp,
  FileText,
  Trash2,
  Sparkles,
  ArrowRight,
  ShieldCheck,
  CheckCircle2,
  AlertCircle,
  Cpu,
  Layers,
} from "lucide-react";

type AnalyzeState = "empty" | "selected" | "uploading" | "processing" | "success" | "error";

export default function AnalyzePage() {
  const [state, setState] = useState<AnalyzeState>("empty");
  const [fileObject, setFileObject] = useState<File | { name: string; size: number; type: string } | null>(null);
  const [fileName, setFileName] = useState<string>("");
  const [fileSize, setFileSize] = useState<string>("");
  const [fileType, setFileType] = useState<string>("");
  const [progress, setProgress] = useState<number>(0);
  const [currentStepIndex, setCurrentStepIndex] = useState<number>(0);
  const [dragActive, setDragActive] = useState<boolean>(false);
  const [extractedPolicy, setExtractedPolicy] = useState<PolicySummary | null>(null);
  const [apiError, setApiError] = useState<ApiError | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const processingSteps = [
    { title: "Uploading Policy", detail: "Securing document upload to local workspace" },
    { title: "Extracting Text", detail: "Running optical character recognition on schedule tables" },
    { title: "Identifying Coverage Rules", detail: "Isolating deductible clauses, copays, and exclusions" },
    { title: "Preparing Coverage Summary", detail: "Generating auditable evidence citations" },
  ];


  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      setFileObject(file);
      setFileName(file.name);
      setFileSize(`${(file.size / (1024 * 1024)).toFixed(2)} MB`);
      setFileType(file.type || "Document");
      setApiError(null);
      setState("selected");
    }
  };

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const file = e.dataTransfer.files[0];
      setFileObject(file);
      setFileName(file.name);
      setFileSize(`${(file.size / (1024 * 1024)).toFixed(2)} MB`);
      setFileType(file.type || "Document");
      setApiError(null);
      setState("selected");
    }
  };

  const startAnalysis = async () => {
    if (!fileObject) return;

    setState("uploading");
    setProgress(15);
    setCurrentStepIndex(0);
    setApiError(null);

    const stepTimer1 = setTimeout(() => {
      setState("processing");
      setProgress(40);
      setCurrentStepIndex(1);
    }, 600);

    const stepTimer2 = setTimeout(() => {
      setProgress(75);
      setCurrentStepIndex(2);
    }, 1200);

    const stepTimer3 = setTimeout(() => {
      setProgress(95);
      setCurrentStepIndex(3);
    }, 1800);

    try {
      const policyResult = await api.uploadPolicy(fileObject);
      clearTimeout(stepTimer1);
      clearTimeout(stepTimer2);
      clearTimeout(stepTimer3);

      setProgress(100);
      setCurrentStepIndex(3);
      setExtractedPolicy(policyResult);
      setState("success");
    } catch (err) {
      clearTimeout(stepTimer1);
      clearTimeout(stepTimer2);
      clearTimeout(stepTimer3);

      const parsed = parseApiError(err);
      setApiError(parsed);
      setState("error");
    }
  };

  const resetAll = () => {
    setState("empty");
    setFileObject(null);
    setFileName("");
    setFileSize("");
    setFileType("");
    setProgress(0);
    setCurrentStepIndex(0);
    setExtractedPolicy(null);
    setApiError(null);
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  const triggerSimulatedError = () => {
    setApiError({
      statusCode: 422,
      code: "DOC_PARSER_EXTRACT_FAIL",
      message: "The OCR layer encountered unreadable table formatting or an unsupported security signature.",
      details: "OCR confidence threshold fell below 60% on page 3. Clause bounding boxes could not be aligned.",
      timestamp: new Date().toISOString(),
    });
    setState("error");
  };

  const activePolicyData = extractedPolicy;

  return (
    <div className="min-h-screen flex flex-col bg-[#F8F9FF] text-[#0A1D2E] antialiased">
      <Header />

      <main className="flex-1 py-10 sm:py-16">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
          {/* Breadcrumb / Status Eyebrow */}
          <div className="mb-6 flex items-center justify-between">
            <div className="flex items-center gap-2 text-xs text-slate-500">
              <Link href="/" className="hover:text-[#0052D1]">
                Home
              </Link>
              <span>/</span>
              <span className="font-semibold text-slate-800">Analyze Policy</span>
            </div>

            <div className="flex items-center gap-2">
              <StatusBadge variant="policy_source" size="xs" label="Document Ingestion" />
            </div>
          </div>

          <SectionHeader
            badge="Policy Ingestion & Extraction"
            badgeVariant="primary"
            title="Upload Your Insurance Policy Schedule"
            description="Upload your Summary of Benefits & Coverage (SBC), policy schedule, or endorsement document. CoverWise AI isolates deductible rules, room rent ceilings, and benefit caps."
          />

          {/* STATE A: Empty State (Upload Area) */}
          {state === "empty" && (
            <Card className="border-slate-200/90 shadow-sm bg-white overflow-hidden">
              <CardContent className="p-8 sm:p-12">
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".pdf,.png,.jpg,.jpeg,.tiff"
                  onChange={handleFileChange}
                  className="hidden"
                  id="policy-file-input"
                  aria-label="Upload insurance policy document"
                />

                <div
                  onDragEnter={handleDrag}
                  onDragLeave={handleDrag}
                  onDragOver={handleDrag}
                  onDrop={handleDrop}
                  className={`border-2 border-dashed rounded-2xl p-8 sm:p-12 text-center flex flex-col items-center justify-center transition-all ${
                    dragActive
                      ? "border-[#1769FF] bg-[#EEF4FF]/50 scale-[1.01]"
                      : "border-slate-300 hover:border-[#1769FF]/50 bg-slate-50/50"
                  }`}
                >
                  <div className="w-16 h-16 rounded-2xl bg-[#EEF4FF] text-[#0052D1] flex items-center justify-center mb-4 shadow-xs">
                    <FileUp className="w-8 h-8 stroke-[1.8]" />
                  </div>

                  <h3 className="text-base sm:text-lg font-bold text-[#0A1D2E] mb-1">
                    Drag and drop your policy document here
                  </h3>
                  <p className="text-xs sm:text-sm text-slate-500 max-w-md mb-6">
                    Supports PDF, PNG, JPG, or TIFF schedules up to 25MB. Multi-layer parsing
                    extracts tabular benefits and room-rent conditions.
                  </p>

                  <div className="flex flex-col sm:flex-row items-center gap-3">
                    <Button
                      variant="primary"
                      size="md"
                      onClick={() => fileInputRef.current?.click()}
                      leftIcon={<FileUp className="w-4 h-4" />}
                    >
                      Browse Files
                    </Button>
                  </div>

                </div>

                {/* Information Callout */}
                <div className="mt-8 pt-6 border-t border-slate-100 grid grid-cols-1 sm:grid-cols-3 gap-4 text-xs text-slate-500">
                  <div className="flex items-start gap-2">
                    <ShieldCheck className="w-4 h-4 text-[#0052D1] shrink-0 mt-0.5" />
                    <span>Local Document Parsing. Zero external training.</span>
                  </div>
                  <div className="flex items-start gap-2">
                    <Cpu className="w-4 h-4 text-[#006B5F] shrink-0 mt-0.5" />
                    <span>Exact table & clause OCR indexing.</span>
                  </div>
                  <div className="flex items-start gap-2">
                    <Layers className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
                    <span>Deterministic formula extraction.</span>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}

          {/* STATE B: Selected File */}
          {state === "selected" && (
            <Card className="border-slate-200 shadow-sm bg-white">
              <CardHeader>
                <div className="flex items-center justify-between">
                  <CardTitle>Selected Policy Document</CardTitle>
                  <Badge variant="teal" size="xs">
                    Ready to Analyze
                  </Badge>
                </div>
                <CardDescription>
                  Confirm your document before extracting coverage rules.
                </CardDescription>
              </CardHeader>

              <CardContent className="space-y-6">
                <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 flex items-center justify-between gap-4">
                  <div className="flex items-center gap-3.5 min-w-0">
                    <div className="w-10 h-10 rounded-xl bg-blue-100 text-[#0052D1] flex items-center justify-center shrink-0">
                      <FileText className="w-5 h-5" />
                    </div>
                    <div className="min-w-0">
                      <p className="font-semibold text-sm text-[#0A1D2E] truncate">{fileName}</p>
                      <p className="text-xs text-slate-500">
                        {fileSize} • {fileType}
                      </p>
                    </div>
                  </div>

                  <Button
                    variant="ghost"
                    size="xs"
                    onClick={resetAll}
                    className="text-slate-400 hover:text-red-600 hover:bg-red-50"
                    aria-label="Remove document"
                  >
                    <Trash2 className="w-4 h-4" />
                  </Button>
                </div>

                <div className="p-4 rounded-xl bg-[#EEF4FF] border border-blue-100 flex items-start gap-3">
                  <AlertCircle className="w-4 h-4 text-[#0052D1] shrink-0 mt-0.5" />
                  <div className="text-xs text-slate-700">
                    <span className="font-semibold">Privacy First:</span> Policy clauses are processed in accordance with strict healthcare data confidentiality principles.
                  </div>
                </div>
              </CardContent>

              <CardFooter className="flex flex-col sm:flex-row items-center justify-between gap-4">
                <Button variant="ghost" size="sm" onClick={resetAll}>
                  Cancel
                </Button>

                <div className="flex items-center gap-2 w-full sm:w-auto">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={triggerSimulatedError}
                    className="text-xs text-slate-500 hover:text-red-600"
                  >
                    Simulate Parser Error
                  </Button>
                  <Button
                    variant="primary"
                    size="md"
                    onClick={startAnalysis}
                    leftIcon={<Sparkles className="w-4 h-4" />}
                    className="w-full sm:w-auto font-semibold"
                  >
                    Start Policy Extraction
                  </Button>
                </div>
              </CardFooter>
            </Card>
          )}

          {/* STATE C & D: Uploading / Processing */}
          {(state === "uploading" || state === "processing") && (
            <Card className="border-slate-200 shadow-sm bg-white p-8">
              <div className="space-y-8">
                <div className="text-center space-y-2">
                  <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-[#EEF4FF] text-[#0052D1] mb-2 shadow-xs">
                    <Cpu className="w-7 h-7 animate-pulse" />
                  </div>
                  <h3 className="text-lg font-bold text-[#0A1D2E]">
                    {state === "uploading"
                      ? "Uploading Policy Document..."
                      : "Extracting Coverage Parameters..."}
                  </h3>
                  <p className="text-xs sm:text-sm text-slate-500 max-w-md mx-auto">
                    Analyzing clause hierarchy and identifying sublimits for{" "}
                    <span className="font-mono font-semibold text-slate-700">{fileName}</span>
                  </p>
                </div>

                <div className="max-w-md mx-auto space-y-2">
                  <div className="flex justify-between text-xs text-slate-500 font-mono">
                    <span>PROGRESS</span>
                    <span>{progress}%</span>
                  </div>
                  <ProgressBar value={progress} max={100} variant="primary" size="md" />
                </div>

                {/* Processing Steps Checklist */}
                <div className="max-w-md mx-auto space-y-3">
                  {processingSteps.map((step, idx) => {
                    const isDone = idx < currentStepIndex;
                    const isCurrent = idx === currentStepIndex;

                    return (
                      <div
                        key={step.title}
                        className={`p-3 rounded-xl border text-xs flex items-center justify-between transition-all ${
                          isDone
                            ? "bg-white border-emerald-200 text-emerald-800 shadow-2xs"
                            : isCurrent
                            ? "bg-[#EEF4FF] border-[#1769FF] text-[#0052D1] shadow-xs"
                            : "bg-slate-50 border-slate-200/70 text-slate-400 opacity-60"
                        }`}
                      >
                        <div className="flex items-center gap-3">
                          <span className="font-mono font-bold text-xs">0{idx + 1}</span>
                          <div>
                            <p className="font-semibold">{step.title}</p>
                            <p className="text-[11px] opacity-80">{step.detail}</p>
                          </div>
                        </div>

                        {isDone ? (
                          <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
                        ) : isCurrent ? (
                          <div className="w-4 h-4 border-2 border-[#1769FF] border-t-transparent rounded-full animate-spin shrink-0" />
                        ) : (
                          <span className="text-[10px] uppercase font-mono">Queued</span>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            </Card>
          )}

          {/* STATE E: Success (Extracted Policy Summary & Categories) */}
          {state === "success" && activePolicyData && (
            <div className="space-y-6">
              {/* Success Banner */}
              <div className="p-4 rounded-2xl bg-[#ECFDF5] border border-emerald-200 flex items-center justify-between gap-4">
                <div className="flex items-center gap-3">
                  <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0" />
                  <div>
                    <h4 className="text-sm font-bold text-emerald-950">
                      Policy Analysis Complete
                    </h4>
                    <p className="text-xs text-emerald-800">
                      Clauses, deductibles, and room-rent conditions successfully extracted from{" "}
                      <span className="font-mono font-semibold">{fileName || activePolicyData.planName}</span>.
                    </p>
                  </div>
                </div>
                <StatusBadge variant="policy_source" size="xs" label="Verified Contract" />
              </div>

              {/* Extracted Policy Card */}
              <Card className="border-slate-200 shadow-sm bg-white">
                <CardHeader className="bg-slate-50/50">
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                    <div>
                      <CardTitle className="text-lg font-bold text-[#0A1D2E]">
                        {displayValueOrNotDetermined(activePolicyData.planName)}
                      </CardTitle>
                      <CardDescription>
                        {displayValueOrNotDetermined(activePolicyData.insurerName)} • Policy No:{" "}
                        <span className="font-mono font-semibold">
                          {displayValueOrNotDetermined(activePolicyData.policyNumber)}
                        </span>
                      </CardDescription>
                    </div>
                    <Badge variant="primary" size="sm">
                      {displayValueOrNotDetermined(activePolicyData.policyPeriod)}
                    </Badge>
                  </div>
                </CardHeader>

                <CardContent className="p-6 space-y-6">
                  {/* Key Extracted Metrics Grid */}
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                    <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-100 flex flex-col gap-1">
                      <span className="text-[11px] font-semibold uppercase text-slate-500">
                        Sum Insured
                      </span>
                      <span className="font-mono text-base sm:text-lg font-bold text-[#0A1D2E]">
                        {formatCurrency(activePolicyData.sumInsured)}
                      </span>
                      <span className="text-[10px] text-slate-400">Annual Limit</span>
                    </div>

                    <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-100 flex flex-col gap-1">
                      <span className="text-[11px] font-semibold uppercase text-slate-500">
                        Annual Deductible
                      </span>
                      <span className="font-mono text-base sm:text-lg font-bold text-[#0A1D2E]">
                        {formatCurrency(activePolicyData.deductible)}
                      </span>
                      <span className="text-[10px] text-slate-400">Individual Tier</span>
                    </div>

                    <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-100 flex flex-col gap-1">
                      <span className="text-[11px] font-semibold uppercase text-slate-500">
                        Mandatory Co-Pay
                      </span>
                      <span className="font-mono text-base sm:text-lg font-bold text-[#0A1D2E]">
                        {displayValueOrNotDetermined(activePolicyData.copayPercent, "", "%")}
                      </span>
                      <span className="text-[10px] text-slate-400">On Major Surgeries</span>
                    </div>

                    <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-100 flex flex-col gap-1">
                      <span className="text-[11px] font-semibold uppercase text-slate-500">
                        Network Type
                      </span>
                      <span className="font-semibold text-xs text-[#006B5F]">
                        {displayValueOrNotDetermined(activePolicyData.networkType)}
                      </span>
                      <span className="text-[10px] text-slate-400">Cashless Admissible</span>
                    </div>
                  </div>

                  {/* Room Rent Ceiling Condition Box */}
                  <div className="p-4 rounded-xl bg-[#EEF4FF] border border-blue-200/80 space-y-1 text-xs">
                    <div className="flex items-center justify-between">
                      <span className="font-semibold text-[#0043AA] uppercase tracking-wider text-[11px]">
                        Extracted Room Rent Clause:
                      </span>
                      <StatusBadge variant="policy_source" size="xs" label="Table 2.4" />
                    </div>
                    <p className="font-medium text-[#0A1D2E]">
                      {displayValueOrNotDetermined(activePolicyData.roomRentLimit)}
                    </p>
                    <p className="text-slate-600 text-[11px] leading-relaxed">
                      {displayValueOrNotDetermined(activePolicyData.roomRentCondition)}
                    </p>
                  </div>

                  {/* Coverage Categories Table */}
                  <div className="space-y-3">
                    <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500">
                      Extracted Coverage Categories:
                    </h4>
                    <div className="divide-y divide-slate-100 border border-slate-200 rounded-xl overflow-hidden text-xs">
                      {activePolicyData.categories?.map((cat) => (
                        <div
                          key={cat.name}
                          className="p-3 bg-white flex items-center justify-between hover:bg-slate-50 transition-colors"
                        >
                          <span className="font-medium text-slate-800">{cat.name}</span>
                          <div className="flex items-center gap-3">
                            {cat.sublimit && (
                              <span className="text-slate-500 font-mono">{cat.sublimit}</span>
                            )}
                            <Badge
                              variant={cat.status.includes("Covered") ? "teal" : cat.status === "Partial" ? "default" : "outline"}
                              size="xs"
                            >
                              {cat.status}
                            </Badge>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                </CardContent>

                <CardFooter className="flex flex-col sm:flex-row items-center justify-between gap-4">
                  <Button variant="ghost" size="sm" onClick={resetAll}>
                    Upload Another Document
                  </Button>

                  <div className="flex flex-wrap items-center gap-2.5 w-full sm:w-auto">
                    <Link href={`/assistant?policyId=${activePolicyData.id}`} className="w-full sm:w-auto">
                      <Button
                        variant="secondary"
                        size="md"
                        leftIcon={<Sparkles className="w-4 h-4 text-[#0052D1]" />}
                        className="w-full sm:w-auto font-semibold border-blue-200 bg-blue-50 text-[#0052D1] hover:bg-blue-100"
                      >
                        Ask Policy Assistant
                      </Button>
                    </Link>

                    <Link href={`/coverage?policyId=${activePolicyData.id}`} className="w-full sm:w-auto">
                      <Button
                        variant="primary"
                        size="md"
                        rightIcon={<ArrowRight className="w-4 h-4" />}
                        className="w-full sm:w-auto font-semibold shadow-md"
                      >
                        Coverage Intelligence
                      </Button>
                    </Link>

                    <Link href={`/simulator?policyId=${activePolicyData.id}`} className="w-full sm:w-auto">
                      <Button
                        variant="outline"
                        size="md"
                        className="w-full sm:w-auto font-semibold border-slate-300"
                      >
                        Scenario Studio
                      </Button>
                    </Link>
                  </div>
                </CardFooter>
              </Card>
            </div>
          )}

          {/* STATE F: Error State */}
          {state === "error" && (
            <Card className="border-red-200 bg-white shadow-sm p-6 sm:p-8">
              <ErrorState
                title={apiError?.code === "NETWORK_ERROR" ? "Network Connection Failed" : "Document Extraction Interrupted"}
                message={apiError?.message || "Unable to parse the policy schedule. The server encountered an error while analyzing document clauses."}
                details={
                  apiError?.details
                    ? typeof apiError.details === "string"
                      ? apiError.details
                      : JSON.stringify(apiError.details)
                    : `Status Code: ${apiError?.statusCode || 500} • Request: ${apiError?.code || "CW_DOC_PARSE_FAIL"}`
                }
                onRetry={startAnalysis}
                retryLabel="Retry Analysis"
              />

              <div className="mt-6 pt-6 border-t border-slate-100 flex flex-wrap justify-center gap-3">
                <Button variant="outline" size="sm" onClick={resetAll}>
                  Choose Another File
                </Button>
              </div>
            </Card>
          )}
        </div>
      </main>

      <Footer />
    </div>
  );
}
