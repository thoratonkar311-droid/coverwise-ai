"use client";

import React, { useState, useEffect, useRef, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { Header } from "@/components/layout/Header";
import { Footer } from "@/components/layout/Footer";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { EvidenceDrawer } from "@/components/coverage/EvidenceDrawer";
import Link from "next/link";
import { api, parseApiError } from "@/lib/api";
import {
  ConversationSession,
  ConversationMessage,
  ConversationEvidence,
  TreatmentEstimateData,
  WhatIfComparisonData,
  PolicySummary,
  ApiError,
} from "@/types";
import { formatCurrency } from "@/lib/utils";
import {
  Sparkles,
  Send,
  FileCheck2,
  FileText,
  AlertTriangle,
  Info,
  ArrowRight,
  ShieldCheck,
  RefreshCw,
  PlusCircle,
  Stethoscope,
  SlidersHorizontal,
  TrendingDown,
  TrendingUp,
  Scale,
  Calculator,
  User,
  Bot,
} from "lucide-react";

const SUGGESTED_QUESTIONS = [
  "Is knee replacement surgery covered under this policy?",
  "What is the waiting period for pre-existing conditions?",
  "Does this policy have a room-rent limit or proportionate deduction?",
  "What if my hospital quote is ₹3,00,000 for knee surgery in Mumbai?",
  "What documents are required to file a reimbursement claim?",
  "Are daycare laparoscopic procedures covered?",
];

const PRESET_PROCEDURES = [
  { name: "Total Knee Replacement", quote: 250000, city: "Mumbai", room: "Single Private Room", stay: 4 },
  { name: "Cataract Surgery with Monofocal IOL", quote: 45000, city: "Delhi NCR", room: "Daycare", stay: 0 },
  { name: "Coronary Angioplasty (PTCA)", quote: 220000, city: "Bengaluru", room: "Single Private Room", stay: 3 },
  { name: "Laparoscopic Appendectomy", quote: 95000, city: "Hyderabad", room: "Twin Sharing", stay: 2 },
  { name: "Laparoscopic Inguinal Hernia Repair", quote: 85000, city: "Pune", room: "Single Private Room", stay: 2 },
];

function AssistantContent() {
  const searchParams = useSearchParams();
  const rawPolicyIdParam = searchParams.get("policyId");
  const initialQueryParam = searchParams.get("q") || "";

  const effectivePolicyId =
    rawPolicyIdParam ||
    (typeof window !== "undefined" ? localStorage.getItem("coverwise_active_policy_id") : null);

  // State
  const [screenState, setScreenState] = useState<"loading" | "ready" | "no_policy" | "error">("loading");
  const [activePolicy, setActivePolicy] = useState<PolicySummary | null>(null);
  const [session, setSession] = useState<ConversationSession | null>(null);
  const [inputMessage, setInputMessage] = useState<string>("");
  const [isSending, setIsSending] = useState<boolean>(false);
  const [apiError, setApiError] = useState<ApiError | null>(null);

  // Scenario Studio Form State
  const [activeTab, setActiveTab] = useState<"chat" | "scenario" | "whatif">("scenario");
  const [procedureName, setProcedureName] = useState<string>("Total Knee Replacement");
  const [hospitalQuote, setHospitalQuote] = useState<number>(250000);
  const [city, setCity] = useState<string>("Mumbai");
  const [hospitalTier, setHospitalTier] = useState<string>("Tier 1 Multi-Specialty Hospital");
  const [roomTier, setRoomTier] = useState<string>("Single Private Room");
  const [isNetworkHospital, setIsNetworkHospital] = useState<boolean>(true);
  const [lengthOfStay, setLengthOfStay] = useState<number>(4);
  const [patientAge, setPatientAge] = useState<number>(54);
  const [preExisting, setPreExisting] = useState<boolean>(false);
  const [isCalculatingEstimate, setIsCalculatingEstimate] = useState<boolean>(false);
  const [currentEstimate, setCurrentEstimate] = useState<TreatmentEstimateData | null>(null);

  // What-If State
  const [whatIfRoomTier, setWhatIfRoomTier] = useState<string>("Deluxe Suite");
  const [whatIfQuote, setWhatIfQuote] = useState<number>(300000);
  const [isEvaluatingWhatIf, setIsEvaluatingWhatIf] = useState<boolean>(false);
  const [whatIfResult, setWhatIfResult] = useState<WhatIfComparisonData | null>(null);

  // Evidence Drawer State
  const [evidenceDrawerOpen, setEvidenceDrawerOpen] = useState<boolean>(false);
  const [selectedEvidence, setSelectedEvidence] = useState<ConversationEvidence | null>(null);

  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Scroll to bottom on new messages
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [session?.messages]);

  // Handle message sending
  const handleSendMessage = async (customContent?: string, targetSessionId?: number) => {
    const textToSend = customContent !== undefined ? customContent : inputMessage;
    if (!textToSend.trim() || isSending || !session) return;

    const sessionId = targetSessionId || session.id;
    setIsSending(true);
    setApiError(null);
    setInputMessage("");

    // Optimistically append user message
    const tempUserMsg: ConversationMessage = {
      id: Date.now(),
      conversationId: sessionId,
      role: "user",
      content: textToSend,
      isGrounded: true,
      evidenceReferences: [],
      createdAt: new Date().toISOString(),
      treatmentScenario: {
        procedureName,
        hospitalQuote,
        city,
        roomTier,
      },
    };

    setSession((prev) => prev ? ({
      ...prev,
      messages: [...prev.messages, tempUserMsg],
    }) : null);

    try {
      const isCostInquiry = /quote|cost|price|estimate|how much|pay|expense|out-of-pocket|calculate/i.test(textToSend);
      const assistantMsg = await api.sendMessage(
        sessionId,
        textToSend,
        isCostInquiry
          ? {
              procedure_name: procedureName,
              hospital_quote: hospitalQuote,
              city,
              room_tier: roomTier,
              hospital_tier: hospitalTier,
              is_network_hospital: isNetworkHospital,
              length_of_stay_days: lengthOfStay,
              patient_age: patientAge,
              pre_existing_condition: preExisting,
            }
          : undefined
      );

      setSession((prev) => prev ? ({
        ...prev,
        messages: [...prev.messages, assistantMsg],
      }) : null);

      if (assistantMsg.costEstimate) {
        setCurrentEstimate(assistantMsg.costEstimate);
      }
    } catch (err) {
      setApiError(parseApiError(err));
    } finally {
      setIsSending(false);
    }
  };

  // Load session or initialize from policyId
  useEffect(() => {
    async function init() {
      setScreenState("loading");
      let targetId = effectivePolicyId;
      if (!targetId) {
        try {
          const overview = await api.getDashboardOverview();
          if (overview.activePolicy) {
            targetId = String(overview.activePolicy.id);
            if (typeof window !== "undefined") {
              localStorage.setItem("coverwise_active_policy_id", targetId);
            }
          }
        } catch {
          // ignore
        }
      }
      if (!targetId) {
        setScreenState("no_policy");
        return;
      }

      try {
        const pol = await api.getPolicyById(targetId);
        if (!pol) {
          setScreenState("no_policy");
          return;
        }
        setActivePolicy(pol);

        const convs = await api.getPolicyConversations(targetId);
        if (convs && convs.length > 0) {
          setSession(convs[0]);
          if (initialQueryParam) {
            handleSendMessage(initialQueryParam, convs[0].id);
          }
        } else {
          const newSession = await api.createConversation(
            targetId,
            initialQueryParam || undefined,
            "Insurance Coverage & Out-of-Pocket Intelligence"
          );
          setSession(newSession);
        }

        // Initialize real deterministic calculation for Scenario Studio
        try {
          const initialEst = await api.estimateTreatmentCost({
            policyId: targetId,
            procedureName,
            hospitalQuote,
            hospitalTier,
            city,
            isNetworkHospital,
            roomTier,
            lengthOfStayDays: lengthOfStay,
            patientAge,
            preExistingCondition: preExisting,
          });
          if (initialEst) setCurrentEstimate(initialEst);
        } catch {
          // user can click button to calculate
        }
        setScreenState("ready");
      } catch (err) {
        setApiError(parseApiError(err));
        setScreenState("error");
      }
    }
    init();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [effectivePolicyId]);

  // Run deterministic treatment cost estimate
  const handleCalculateEstimate = async () => {
    const targetPolicyId = activePolicy?.id || effectivePolicyId;
    if (!targetPolicyId) {
      setApiError(parseApiError(new Error("No active policy selected.")));
      return;
    }
    setIsCalculatingEstimate(true);
    setApiError(null);
    try {
      const estimate = await api.estimateTreatmentCost({
        policyId: targetPolicyId,
        procedureName,
        hospitalQuote,
        hospitalTier,
        city,
        isNetworkHospital,
        roomTier,
        lengthOfStayDays: lengthOfStay,
        patientAge,
        preExistingCondition: preExisting,
      });
      setCurrentEstimate(estimate);
    } catch (err) {
      setApiError(parseApiError(err));
    } finally {
      setIsCalculatingEstimate(false);
    }
  };

  // Run What-If analysis
  const handleEvaluateWhatIf = async () => {
    const targetPolicyId = activePolicy?.id || effectivePolicyId;
    if (!targetPolicyId) {
      setApiError(parseApiError(new Error("No active policy selected.")));
      return;
    }
    setIsEvaluatingWhatIf(true);
    setApiError(null);
    try {
      const previousScenario = {
        procedure_name: procedureName,
        hospital_quote: hospitalQuote,
        hospital_tier: hospitalTier,
        city,
        is_network_hospital: isNetworkHospital,
        room_tier: roomTier,
        length_of_stay_days: lengthOfStay,
        patient_age: patientAge,
      };

      const updatedScenario = {
        ...previousScenario,
        hospital_quote: whatIfQuote,
        room_tier: whatIfRoomTier,
      };

      const result = await api.evaluateWhatIf({
        policyId: targetPolicyId,
        previousScenario,
        updatedScenario,
      });

      setWhatIfResult(result);
      setActiveTab("whatif");
    } catch (err) {
      setApiError(parseApiError(err));
    } finally {
      setIsEvaluatingWhatIf(false);
    }
  };

  const handleApplyPreset = (preset: (typeof PRESET_PROCEDURES)[0]) => {
    setProcedureName(preset.name);
    setHospitalQuote(preset.quote);
    setCity(preset.city);
    setRoomTier(preset.room);
    setLengthOfStay(preset.stay);
  };

  const openEvidence = (ev: ConversationEvidence) => {
    setSelectedEvidence(ev);
    setEvidenceDrawerOpen(true);
  };

  const handleNewConversation = async () => {
    const targetPolicyId = activePolicy?.id || effectivePolicyId;
    if (!targetPolicyId) return;
    try {
      const newSess = await api.createConversation(
        targetPolicyId,
        undefined,
        "New Insurance Consultation Session"
      );
      setSession(newSess);
      setCurrentEstimate(null);
      setWhatIfResult(null);
    } catch (err) {
      setApiError(parseApiError(err));
    }
  };

  return (
    <div className="min-h-screen flex flex-col bg-[#F8FAFC]">
      <Header />

      {screenState === "loading" && (
        <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-16 flex items-center justify-center">
          <div className="flex flex-col items-center gap-3 text-slate-500">
            <div className="w-8 h-8 border-3 border-[#0052D1] border-t-transparent rounded-full animate-spin" />
            <p className="text-sm font-medium">Loading active policy intelligence...</p>
          </div>
        </main>
      )}

      {screenState === "no_policy" && (
        <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-16">
          <div className="max-w-xl mx-auto text-center p-8 bg-white rounded-2xl border border-slate-200/80 shadow-sm space-y-4">
            <div className="w-14 h-14 rounded-2xl bg-blue-50 text-[#0052D1] flex items-center justify-center mx-auto">
              <FileText className="w-7 h-7" />
            </div>
            <h2 className="text-xl font-bold text-[#0A1D2E]">No Active Policy Selected</h2>
            <p className="text-sm text-slate-500 leading-relaxed">
              Please select an insurance policy from your dashboard or upload a new policy document to begin grounded assistant consultations, scenario analysis, and out-of-pocket calculations.
            </p>
            <div className="flex justify-center gap-3 pt-2">
              <Link href="/dashboard">
                <Button variant="outline" size="sm">Go to Dashboard</Button>
              </Link>
              <Link href="/upload">
                <Button variant="primary" size="sm">Upload Policy</Button>
              </Link>
            </div>
          </div>
        </main>
      )}

      {screenState === "error" && (
        <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-16">
          <div className="max-w-xl mx-auto text-center p-8 bg-white rounded-2xl border border-red-200 shadow-sm space-y-4">
            <div className="w-14 h-14 rounded-2xl bg-red-50 text-red-600 flex items-center justify-center mx-auto">
              <AlertTriangle className="w-7 h-7" />
            </div>
            <h2 className="text-xl font-bold text-[#0A1D2E]">Unable to Load Policy</h2>
            <p className="text-sm text-slate-500 leading-relaxed">
              {apiError?.message || "An error occurred while loading this policy's conversation session."}
            </p>
            <div className="flex justify-center gap-3 pt-2">
              <Button variant="outline" size="sm" onClick={() => window.location.reload()}>Retry</Button>
              <Link href="/dashboard">
                <Button variant="primary" size="sm">Return to Dashboard</Button>
              </Link>
            </div>
          </div>
        </main>
      )}

      {screenState === "ready" && activePolicy && session && (
        <>
          {/* Hero / Header Bar */}
          <section className="bg-gradient-to-r from-[#0A1D2E] via-[#0D2847] to-[#0A1D2E] text-white py-6 border-b border-slate-800">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <div>
                  <div className="flex items-center gap-2 mb-1">
                    <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-blue-500/20 text-blue-300 border border-blue-400/30">
                      <Sparkles className="w-3.5 h-3.5 text-blue-300" /> Grounded Policy Intelligence
                    </span>
                    <span className="text-xs text-slate-400 font-mono">Session #{session.id}</span>
                  </div>
                  <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-white flex items-center gap-2">
                    Policy Intelligence Assistant
                  </h1>
                  <p className="text-xs sm:text-sm text-slate-300">
                    Grounded multi-turn answers with verbatim citations & deterministic out-of-pocket calculations.
                  </p>
                </div>

                {/* Active Policy Capsule */}
                <div className="flex items-center gap-3 p-3 rounded-xl bg-white/5 border border-white/10 backdrop-blur-xs">
                  <div className="w-9 h-9 rounded-lg bg-[#0052D1] flex items-center justify-center text-white shrink-0 shadow-sm">
                    <ShieldCheck className="w-5 h-5" />
                  </div>
                  <div className="flex flex-col text-xs">
                    <span className="font-semibold text-white line-clamp-1">{activePolicy.planName}</span>
                    <span className="text-slate-400 text-[11px]">
                      Sum Insured: {formatCurrency(activePolicy.sumInsured)} • Ded: {activePolicy.deductible != null ? formatCurrency(activePolicy.deductible) : "Not Determined"}
                    </span>
                  </div>
                  <Button
                    variant="ghost"
                    size="xs"
                    onClick={handleNewConversation}
                    className="text-slate-300 hover:text-white hover:bg-white/10 ml-2"
                    title="Start a new conversation session"
                  >
                    <PlusCircle className="w-4 h-4 mr-1" /> New
                  </Button>
                </div>
              </div>
            </div>
          </section>

          {/* Main Studio Body: 2-Column Responsive Layout */}
          <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
          
          {/* LEFT COLUMN: Conversational Chat Interface (7 Cols on desktop) */}
          <div className="lg:col-span-7 flex flex-col h-[740px] bg-white rounded-2xl border border-slate-200/80 shadow-sm overflow-hidden">
            
            {/* Session Top Bar & Quick Prompts */}
            <div className="p-3.5 bg-slate-50/80 border-b border-slate-200/70 space-y-2">
              <div className="flex items-center justify-between text-xs text-slate-600 font-medium px-1">
                <span className="flex items-center gap-1.5 font-semibold text-[#0A1D2E]">
                  <Bot className="w-4 h-4 text-[#0052D1]" /> Policy Audit & Coverage Dialogue
                </span>
                <span className="text-[11px] text-slate-500">
                  {session.messages.length} message{session.messages.length === 1 ? "" : "s"}
                </span>
              </div>

              {/* Quick Prompt Chips */}
              <div className="flex items-center gap-1.5 overflow-x-auto pb-1 scrollbar-none text-[11px]">
                <span className="text-[10px] uppercase font-bold text-slate-500 shrink-0 mr-1">
                  Ask:
                </span>
                {SUGGESTED_QUESTIONS.slice(0, 4).map((q, idx) => (
                  <button
                    key={idx}
                    onClick={() => handleSendMessage(q)}
                    disabled={isSending}
                    className="shrink-0 px-2.5 py-1 rounded-full bg-white border border-slate-200 text-slate-700 hover:border-blue-300 hover:bg-blue-50/60 hover:text-[#0052D1] transition-all cursor-pointer text-left font-medium"
                  >
                    {q}
                  </button>
                ))}
              </div>
            </div>

            {/* Chat Messages Transcript Area */}
            <div className="flex-1 overflow-y-auto p-4 sm:p-5 space-y-4 bg-slate-50/30">
              {session.messages.length === 0 ? (
                <div className="h-full flex flex-col items-center justify-center text-center p-6 text-slate-500">
                  <div className="w-12 h-12 rounded-2xl bg-blue-50 text-[#0052D1] flex items-center justify-center mb-3">
                    <Sparkles className="w-6 h-6" />
                  </div>
                  <h3 className="text-sm font-bold text-[#0A1D2E] mb-1">
                    Ask anything about this health policy
                  </h3>
                  <p className="text-xs text-slate-500 max-w-sm">
                    Inquire about surgical procedures, waiting periods, room rent penalties, or claim documentation requirements.
                  </p>
                </div>
              ) : (
                session.messages.map((msg) => {
                  const isUser = msg.role === "user";
                  return (
                    <div
                      key={msg.id}
                      className={`flex gap-3 ${isUser ? "justify-end" : "justify-start"}`}
                    >
                      {!isUser && (
                        <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-[#0052D1] to-[#1769FF] text-white flex items-center justify-center shrink-0 shadow-sm mt-0.5">
                          <Bot className="w-4 h-4" />
                        </div>
                      )}

                      <div
                        className={`flex flex-col max-w-[85%] sm:max-w-[80%] rounded-2xl p-4 space-y-3 ${
                          isUser
                            ? "bg-[#0A1D2E] text-white rounded-tr-xs shadow-sm"
                            : "bg-white text-slate-800 border border-slate-200/90 rounded-tl-xs shadow-xs"
                        }`}
                      >
                        {/* Header for assistant message */}
                        {!isUser && (
                          <div className="flex items-center justify-between gap-2 border-b border-slate-100 pb-2">
                            <div className="flex items-center gap-1.5">
                              <span className="text-xs font-bold text-[#0A1D2E]">CoverWise Assistant</span>
                              {msg.confidence && (
                                <Badge
                                  variant={
                                    msg.confidence === "High"
                                      ? "teal"
                                      : msg.confidence === "Medium"
                                      ? "primary"
                                      : "outline"
                                  }
                                  size="xs"
                                >
                                  {msg.confidence} Confidence
                                </Badge>
                              )}
                            </div>
                            <span className="text-[10px] text-slate-500">
                              {new Date(msg.createdAt).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                            </span>
                          </div>
                        )}

                        {/* Content text */}
                        <div className={`text-xs sm:text-[13px] leading-relaxed whitespace-pre-line ${isUser ? "text-slate-100" : "text-slate-800"}`}>
                          {msg.content}
                        </div>

                        {/* Uncertainty Reason Alert (if present) */}
                        {!isUser && msg.uncertaintyReason && (
                          <div className="p-2.5 rounded-lg bg-amber-50/90 border border-amber-200/80 text-[11px] text-amber-900 flex items-start gap-2">
                            <AlertTriangle className="w-3.5 h-3.5 text-amber-600 shrink-0 mt-0.5" />
                            <div>
                              <span className="font-semibold">Uncertainty Note: </span>
                              {msg.uncertaintyReason}
                            </div>
                          </div>
                        )}

                        {/* Grounded Evidence Citations Badge/List */}
                        {!isUser && msg.evidenceReferences && msg.evidenceReferences.length > 0 && (
                          <div className="space-y-1.5 pt-1">
                            <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500 flex items-center gap-1">
                              <FileCheck2 className="w-3 h-3 text-[#0052D1]" /> Grounded Policy Evidence:
                            </span>
                            <div className="flex flex-wrap gap-1.5">
                              {msg.evidenceReferences.map((ev, idx) => (
                                <button
                                  key={idx}
                                  onClick={() => openEvidence(ev)}
                                  className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-[#EEF4FF] hover:bg-blue-100 border border-blue-200 text-[#0052D1] text-[11px] font-medium transition-colors cursor-pointer text-left"
                                >
                                  <FileText className="w-3 h-3" />
                                  <span>{ev.clauseSection || `Page ${ev.page}`}</span>
                                  {ev.page && <span className="text-[10px] text-blue-400 font-mono">(p. {ev.page})</span>}
                                </button>
                              ))}
                            </div>
                          </div>
                        )}

                        {/* Inline Cost Estimate Card (if turn returned calculation) */}
                        {!isUser && msg.costEstimate && (
                          <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200/80 space-y-2 mt-2">
                            <div className="flex items-center justify-between text-xs">
                              <span className="font-bold text-[#0A1D2E] flex items-center gap-1">
                                <Stethoscope className="w-3.5 h-3.5 text-[#0052D1]" />
                                {msg.costEstimate.treatmentName}
                              </span>
                              <Badge variant="teal" size="xs">
                                {msg.costEstimate.coverageStatus}
                              </Badge>
                            </div>

                            <div className="grid grid-cols-2 gap-2 text-xs pt-1">
                              <div className="p-2 rounded-lg bg-emerald-50/80 border border-emerald-100 flex flex-col">
                                <span className="text-[10px] font-semibold uppercase text-emerald-800">
                                  Insurer Pays
                                </span>
                                <span className="font-mono text-sm font-bold text-emerald-900">
                                  {formatCurrency(msg.costEstimate.estimatedInsurerContribution)}
                                </span>
                              </div>

                              <div className="p-2 rounded-lg bg-rose-50/80 border border-rose-100 flex flex-col">
                                <span className="text-[10px] font-semibold uppercase text-rose-800">
                                  You Pay (Out-of-Pocket)
                                </span>
                                <span className="font-mono text-sm font-bold text-rose-900">
                                  {formatCurrency(msg.costEstimate.estimatedPatientResponsibility)}
                                </span>
                              </div>
                            </div>

                            <button
                              onClick={() => {
                                if (msg.costEstimate) setCurrentEstimate(msg.costEstimate);
                                setActiveTab("scenario");
                              }}
                              className="text-[11px] text-[#0052D1] hover:underline font-semibold flex items-center gap-1 pt-1 cursor-pointer"
                            >
                              Inspect Detailed Deductions in Studio <ArrowRight className="w-3 h-3" />
                            </button>
                          </div>
                        )}

                        {/* Disclaimer */}
                        {!isUser && (
                          <div className="text-[10px] text-slate-500 pt-1 border-t border-slate-100 italic">
                            {msg.costEstimate?.disclaimer || "Indicative estimate based on extracted policy rules. Final claim settlement depends on hospital discharge summary."}
                          </div>
                        )}
                      </div>

                      {isUser && (
                        <div className="w-8 h-8 rounded-lg bg-[#0A1D2E] text-white flex items-center justify-center shrink-0 shadow-sm mt-0.5">
                          <User className="w-4 h-4" />
                        </div>
                      )}
                    </div>
                  );
                })
              )}
              <div ref={messagesEndRef} />
            </div>

            {/* Error Banner */}
            {apiError && (
              <div className="px-4 py-2 bg-rose-50 border-t border-rose-200 text-xs text-rose-700 flex items-center justify-between">
                <span>{apiError.message || "Failed to communicate with assistant service."}</span>
                <Button variant="ghost" size="xs" onClick={() => setApiError(null)}>Dismiss</Button>
              </div>
            )}

            {/* Chat Input Bar */}
            <div className="p-3.5 bg-white border-t border-slate-200/80">
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  handleSendMessage();
                }}
                className="flex items-end gap-2"
              >
                <div className="flex-1 relative">
                  <textarea
                    rows={2}
                    value={inputMessage}
                    onChange={(e) => setInputMessage(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" && !e.shiftKey) {
                        e.preventDefault();
                        handleSendMessage();
                      }
                    }}
                    placeholder="Ask about coverage, room rent limits, pre-existing diseases, or hospital quotes..."
                    className="w-full resize-none rounded-xl border border-slate-300 px-3.5 py-2.5 text-xs text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-[#0052D1] focus:border-transparent transition-all"
                  />
                  <div className="text-[10px] text-slate-500 absolute bottom-1 right-2 pointer-events-none hidden sm:block">
                    Press Enter ↵ to send
                  </div>
                </div>

                <Button
                  type="submit"
                  variant="primary"
                  size="md"
                  disabled={!inputMessage.trim() || isSending}
                  className="h-10 px-4 shrink-0 shadow-sm"
                >
                  {isSending ? (
                    <RefreshCw className="w-4 h-4 animate-spin" />
                  ) : (
                    <Send className="w-4 h-4" />
                  )}
                </Button>
              </form>
            </div>
          </div>

          {/* RIGHT COLUMN: Treatment Scenario & What-If Studio (5 Cols on desktop) */}
          <div className="lg:col-span-5 space-y-4">
            
            {/* Mode Switch Tabs */}
            <div className="flex items-center p-1 bg-slate-200/70 rounded-xl text-xs font-semibold">
              <button
                onClick={() => setActiveTab("scenario")}
                className={`flex-1 py-2 px-3 rounded-lg transition-all flex items-center justify-center gap-1.5 cursor-pointer ${
                  activeTab === "scenario"
                    ? "bg-white text-[#0A1D2E] shadow-xs font-bold"
                    : "text-slate-600 hover:text-slate-900"
                }`}
              >
                <Stethoscope className="w-3.5 h-3.5 text-[#0052D1]" />
                Scenario Studio
              </button>

              <button
                onClick={() => setActiveTab("whatif")}
                className={`flex-1 py-2 px-3 rounded-lg transition-all flex items-center justify-center gap-1.5 cursor-pointer ${
                  activeTab === "whatif"
                    ? "bg-white text-[#0A1D2E] shadow-xs font-bold"
                    : "text-slate-600 hover:text-slate-900"
                }`}
              >
                <Scale className="w-3.5 h-3.5 text-[#0052D1]" />
                What-If Lab
              </button>
            </div>

            {/* TAB A: SCENARIO STUDIO */}
            {activeTab === "scenario" && (
              <Card className="bg-white border-slate-200/80 shadow-sm">
                <CardHeader className="pb-3 border-b border-slate-100">
                  <div className="flex items-center justify-between">
                    <div>
                      <CardTitle className="text-sm font-bold text-[#0A1D2E] flex items-center gap-1.5">
                        <SlidersHorizontal className="w-4 h-4 text-[#0052D1]" />
                        Structured Treatment Scenario
                      </CardTitle>
                      <CardDescription className="text-xs">
                        Configure clinical parameters for deterministic calculation
                      </CardDescription>
                    </div>
                    <Badge variant="outline" size="xs">Deterministic</Badge>
                  </div>
                </CardHeader>

                <CardContent className="p-4 sm:p-5 space-y-4">
                  {/* Preset Procedure Quick Picks */}
                  <div className="space-y-1.5">
                    <label className="text-[11px] font-bold uppercase tracking-wider text-slate-500">
                      Quick Benchmark Presets:
                    </label>
                    <div className="flex flex-wrap gap-1.5">
                      {PRESET_PROCEDURES.map((p, i) => (
                        <button
                          key={i}
                          onClick={() => handleApplyPreset(p)}
                          className={`text-[11px] px-2.5 py-1 rounded-md border transition-all cursor-pointer ${
                            procedureName === p.name
                              ? "bg-[#EEF4FF] border-blue-400 text-[#0052D1] font-semibold"
                              : "bg-white border-slate-200 text-slate-700 hover:bg-slate-50"
                          }`}
                        >
                          {p.name.split(" ")[0]} {p.name.split(" ")[1] || ""}
                        </button>
                      ))}
                    </div>
                  </div>

                  {/* Form Fields Grid */}
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
                    <div className="sm:col-span-2 space-y-1">
                      <label className="font-semibold text-slate-700">Procedure Name</label>
                      <input
                        type="text"
                        value={procedureName}
                        onChange={(e) => setProcedureName(e.target.value)}
                        className="w-full px-3 py-1.5 rounded-lg border border-slate-300 text-slate-900 focus:outline-none focus:ring-1 focus:ring-[#0052D1]"
                      />
                    </div>

                    <div className="space-y-1">
                      <label className="font-semibold text-slate-700">Hospital Quote (₹)</label>
                      <input
                        type="number"
                        step="5000"
                        value={hospitalQuote}
                        onChange={(e) => setHospitalQuote(Number(e.target.value))}
                        className="w-full px-3 py-1.5 rounded-lg border border-slate-300 font-mono text-slate-900 focus:outline-none focus:ring-1 focus:ring-[#0052D1]"
                      />
                    </div>

                    <div className="space-y-1">
                      <label className="font-semibold text-slate-700">City / Region</label>
                      <select
                        value={city}
                        onChange={(e) => setCity(e.target.value)}
                        className="w-full px-3 py-1.5 rounded-lg border border-slate-300 text-slate-900 bg-white focus:outline-none focus:ring-1 focus:ring-[#0052D1]"
                      >
                        <option value="Mumbai">Mumbai (Tier 1)</option>
                        <option value="Delhi NCR">Delhi NCR (Tier 1)</option>
                        <option value="Bengaluru">Bengaluru (Tier 1)</option>
                        <option value="Hyderabad">Hyderabad (Tier 1)</option>
                        <option value="Pune">Pune (Tier 2)</option>
                        <option value="Chennai">Chennai (Tier 1)</option>
                      </select>
                    </div>

                    <div className="space-y-1">
                      <label className="font-semibold text-slate-700">Room Category</label>
                      <select
                        value={roomTier}
                        onChange={(e) => setRoomTier(e.target.value)}
                        className="w-full px-3 py-1.5 rounded-lg border border-slate-300 text-slate-900 bg-white focus:outline-none focus:ring-1 focus:ring-[#0052D1]"
                      >
                        <option value="Single Private Room">Single Private Room</option>
                        <option value="Twin Sharing">Twin Sharing Room</option>
                        <option value="Deluxe Suite">Deluxe Suite</option>
                        <option value="General Ward">General Ward</option>
                        <option value="Daycare">Daycare (No Room Rent)</option>
                      </select>
                    </div>

                    <div className="space-y-1">
                      <label className="font-semibold text-slate-700">Length of Stay (Days)</label>
                      <input
                        type="number"
                        min="0"
                        max="30"
                        value={lengthOfStay}
                        onChange={(e) => setLengthOfStay(Number(e.target.value))}
                        className="w-full px-3 py-1.5 rounded-lg border border-slate-300 font-mono text-slate-900 focus:outline-none focus:ring-1 focus:ring-[#0052D1]"
                      />
                    </div>

                    <div className="space-y-1">
                      <label className="font-semibold text-slate-700">Hospital Tier</label>
                      <select
                        value={hospitalTier}
                        onChange={(e) => setHospitalTier(e.target.value)}
                        className="w-full px-3 py-1.5 rounded-lg border border-slate-300 text-slate-900 bg-white focus:outline-none focus:ring-1 focus:ring-[#0052D1]"
                      >
                        <option value="Tier 1 Multi-Specialty Hospital">Tier 1 Multi-Specialty</option>
                        <option value="Tier 2 Multi-Specialty Hospital">Tier 2 Hospital</option>
                        <option value="Daycare Specialty Center">Daycare Specialty Clinic</option>
                      </select>
                    </div>

                    <div className="space-y-1">
                      <label className="font-semibold text-slate-700">Patient Age</label>
                      <input
                        type="number"
                        min="1"
                        max="100"
                        value={patientAge}
                        onChange={(e) => setPatientAge(Number(e.target.value))}
                        className="w-full px-3 py-1.5 rounded-lg border border-slate-300 font-mono text-slate-900 focus:outline-none focus:ring-1 focus:ring-[#0052D1]"
                      />
                    </div>

                    <div className="flex flex-col gap-2 pt-2 sm:col-span-2">
                      <div className="flex items-center gap-2">
                        <input
                          type="checkbox"
                          id="netHosp"
                          checked={isNetworkHospital}
                          onChange={(e) => setIsNetworkHospital(e.target.checked)}
                          className="rounded border-slate-300 text-[#0052D1] focus:ring-[#0052D1]"
                        />
                        <label htmlFor="netHosp" className="text-xs font-medium text-slate-700 cursor-pointer">
                          Cashless Network Hospital
                        </label>
                      </div>

                      <div className="flex items-center gap-2">
                        <input
                          type="checkbox"
                          id="preExisting"
                          checked={preExisting}
                          onChange={(e) => setPreExisting(e.target.checked)}
                          className="rounded border-slate-300 text-[#0052D1] focus:ring-[#0052D1]"
                        />
                        <label htmlFor="preExisting" className="text-xs font-medium text-slate-700 cursor-pointer">
                          Pre-Existing Condition (Subject to Policy Waiting Periods)
                        </label>
                      </div>
                    </div>
                  </div>

                  <Button
                    variant="primary"
                    size="sm"
                    onClick={handleCalculateEstimate}
                    disabled={isCalculatingEstimate}
                    className="w-full justify-center font-semibold shadow-xs"
                  >
                    {isCalculatingEstimate ? (
                      <RefreshCw className="w-4 h-4 animate-spin mr-1.5" />
                    ) : (
                      <Calculator className="w-4 h-4 mr-1.5" />
                    )}
                    Calculate Deterministic Estimate
                  </Button>

                  {/* ESTIMATE RESULTS BREAKDOWN */}
                  {currentEstimate && (
                    <div className="p-4 rounded-xl bg-slate-50 border border-slate-200/90 space-y-3.5 mt-3">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-bold text-[#0A1D2E] uppercase tracking-wider">
                          Out-of-Pocket Breakdown
                        </span>
                        <div className="flex items-center gap-1.5">
                          {currentEstimate.deductibleStatus === "not_determined" && (
                            <Badge variant="outline" size="xs" className="border-amber-400 text-amber-800 bg-amber-50">
                              Conditional on ₹0 Deductible
                            </Badge>
                          )}
                          <Badge variant="teal" size="xs">
                            {currentEstimate.coverageStatus}
                          </Badge>
                        </div>
                      </div>

                      {currentEstimate.deductibleStatus === "not_determined" && (
                        <div className="p-2.5 rounded-lg bg-amber-50/80 border border-amber-200 text-[11px] text-amber-900 flex items-start gap-2">
                          <Info className="w-3.5 h-3.5 text-amber-600 shrink-0 mt-0.5" />
                          <span>
                            <strong>Deductible Not Determined:</strong> Policy terms do not establish a deductible amount. This calculation is conditional on no deductible (₹0) being applied upon claim adjudication.
                          </span>
                        </div>
                      )}

                      {/* Stat Cards */}
                      <div className="grid grid-cols-2 gap-2.5">
                        <div className="p-2.5 rounded-lg bg-emerald-50 border border-emerald-200 flex flex-col">
                          <span className="text-[10px] font-bold uppercase text-emerald-800">
                            Insurer Share
                          </span>
                          <span className="font-mono text-lg font-bold text-emerald-900">
                            {formatCurrency(currentEstimate.estimatedInsurerContribution)}
                          </span>
                          <span className="text-[10px] text-emerald-700">
                            {Math.round(
                              (currentEstimate.estimatedInsurerContribution /
                                (currentEstimate.estimatedTotalCost || 1)) *
                                100
                            )}
                            % of billed charges
                          </span>
                        </div>

                        <div className="p-2.5 rounded-lg bg-rose-50 border border-rose-200 flex flex-col">
                          <span className="text-[10px] font-bold uppercase text-rose-800">
                            You Pay (Patient)
                          </span>
                          <span className="font-mono text-lg font-bold text-rose-900">
                            {formatCurrency(currentEstimate.estimatedPatientResponsibility)}
                          </span>
                          <span className="text-[10px] text-rose-700">
                            {Math.round(
                              (currentEstimate.estimatedPatientResponsibility /
                                (currentEstimate.estimatedTotalCost || 1)) *
                                100
                            )}
                            % out-of-pocket
                          </span>
                        </div>
                      </div>

                      {/* Itemized Deductions */}
                      <div className="space-y-1.5 text-xs divide-y divide-slate-200/60 pt-1">
                        <div className="flex items-center justify-between py-1 text-slate-600">
                          <span>Total Billed Treatment Cost</span>
                          <span className="font-mono font-semibold text-slate-800">
                            {formatCurrency(currentEstimate.estimatedTotalCost)}
                          </span>
                        </div>
                        <div className="flex items-center justify-between py-1 text-slate-600">
                          <span>Policy Deductible</span>
                          <span className={`font-mono font-semibold ${
                            currentEstimate.deductibleStatus === "not_determined" 
                              ? "text-slate-500 italic text-[11px]" 
                              : "text-rose-600"
                          }`}>
                            {currentEstimate.deductibleStatus === "not_determined"
                              ? "Not Determined"
                              : currentEstimate.deductibleApplied > 0
                              ? `+${formatCurrency(currentEstimate.deductibleApplied)}`
                              : "₹0"}
                          </span>
                        </div>
                        <div className="flex items-center justify-between py-1 text-slate-600">
                          <span>Co-payment Amount</span>
                          <span className="font-mono font-semibold text-rose-600">
                            +{formatCurrency(currentEstimate.copayApplied)}
                          </span>
                        </div>
                        {currentEstimate.roomRentPenalty > 0 && (
                          <div className="flex items-center justify-between py-1 text-amber-700 font-medium">
                            <span>Room Rent Proportionate Penalty</span>
                            <span className="font-mono font-semibold text-rose-600">
                              +{formatCurrency(currentEstimate.roomRentPenalty)}
                            </span>
                          </div>
                        )}
                        {currentEstimate.excessOverLimit > 0 && (
                          <div className="flex items-center justify-between py-1 text-amber-700 font-medium">
                            <span>Sub-Limit Overflow</span>
                            <span className="font-mono font-semibold text-rose-600">
                              +{formatCurrency(currentEstimate.excessOverLimit)}
                            </span>
                          </div>
                        )}
                      </div>

                      {/* Driving Factors */}
                      {currentEstimate.drivingFactors && currentEstimate.drivingFactors.length > 0 && (
                        <div className="space-y-1.5 pt-1">
                          <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500">
                            Driving Cost Factors:
                          </span>
                          <div className="space-y-1">
                            {currentEstimate.drivingFactors.map((df, i) => (
                              <div
                                key={i}
                                className="text-[11px] p-2 rounded-md bg-white border border-slate-200/70 text-slate-700 space-y-0.5"
                              >
                                <div className="flex items-center justify-between font-semibold text-[#0A1D2E]">
                                  <span>{df.factorName}</span>
                                  {df.impactAmount ? (
                                    <span className="font-mono text-rose-600">
                                      +{formatCurrency(df.impactAmount)}
                                    </span>
                                  ) : null}
                                </div>
                                <p className="text-slate-500 text-[10px]">{df.description}</p>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* CTA to test What-If */}
                      <div className="pt-2">
                        <Button
                          variant="secondary"
                          size="xs"
                          onClick={() => {
                            setWhatIfQuote(hospitalQuote + 50000);
                            setWhatIfRoomTier(roomTier === "Single Private Room" ? "Deluxe Suite" : "Single Private Room");
                            handleEvaluateWhatIf();
                          }}
                          className="w-full text-xs font-semibold text-[#0052D1] border-blue-200 bg-blue-50/70 hover:bg-blue-100"
                        >
                          Simulate & Compare in What-If Lab <ArrowRight className="w-3.5 h-3.5 ml-1" />
                        </Button>
                      </div>
                    </div>
                  )}
                </CardContent>
              </Card>
            )}

            {/* TAB B: WHAT-IF LAB */}
            {activeTab === "whatif" && (
              <Card className="bg-white border-slate-200/80 shadow-sm">
                <CardHeader className="pb-3 border-b border-slate-100">
                  <div className="flex items-center justify-between">
                    <div>
                      <CardTitle className="text-sm font-bold text-[#0A1D2E] flex items-center gap-1.5">
                        <Scale className="w-4 h-4 text-[#0052D1]" />
                        What-If Impact Lab
                      </CardTitle>
                      <CardDescription className="text-xs">
                        See how out-of-pocket costs swing when inputs or room choices change
                      </CardDescription>
                    </div>
                    <Badge variant="teal" size="xs">Comparative Analysis</Badge>
                  </div>
                </CardHeader>

                <CardContent className="p-4 sm:p-5 space-y-4">
                  {/* Scenario Comparison Inputs */}
                  <div className="p-3 rounded-xl bg-slate-50 border border-slate-200/80 space-y-3 text-xs">
                    <span className="text-[11px] font-bold uppercase tracking-wider text-slate-600 block">
                      Modify Alternative Scenario:
                    </span>

                    <div className="space-y-1">
                      <label className="font-semibold text-slate-700">Alternative Hospital Quote (₹)</label>
                      <input
                        type="number"
                        step="10000"
                        value={whatIfQuote}
                        onChange={(e) => setWhatIfQuote(Number(e.target.value))}
                        className="w-full px-3 py-1.5 rounded-lg border border-slate-300 font-mono text-slate-900 bg-white"
                      />
                    </div>

                    <div className="space-y-1">
                      <label className="font-semibold text-slate-700">Alternative Room Category</label>
                      <select
                        value={whatIfRoomTier}
                        onChange={(e) => setWhatIfRoomTier(e.target.value)}
                        className="w-full px-3 py-1.5 rounded-lg border border-slate-300 text-slate-900 bg-white"
                      >
                        <option value="Single Private Room">Single Private Room</option>
                        <option value="Deluxe Suite">Deluxe Suite</option>
                        <option value="Twin Sharing">Twin Sharing Room</option>
                      </select>
                    </div>

                    <Button
                      variant="primary"
                      size="sm"
                      onClick={handleEvaluateWhatIf}
                      disabled={isEvaluatingWhatIf}
                      className="w-full justify-center font-semibold shadow-xs"
                    >
                      {isEvaluatingWhatIf ? (
                        <RefreshCw className="w-4 h-4 animate-spin mr-1.5" />
                      ) : (
                        <Scale className="w-4 h-4 mr-1.5" />
                      )}
                      Run What-If Comparison
                    </Button>
                  </div>

                  {/* COMPARISON RESULTS */}
                  {whatIfResult ? (
                    <div className="space-y-3 pt-1">
                      {/* Delta Summary Box */}
                      <div className="p-3.5 rounded-xl bg-blue-50/70 border border-blue-200/80 space-y-2">
                        <div className="flex items-center justify-between text-xs">
                          <span className="font-bold text-[#0043AA] uppercase tracking-wider">
                            Cost Swing Comparison
                          </span>
                          <span className="text-[11px] font-semibold text-slate-600">
                            Baseline vs Modified
                          </span>
                        </div>

                        <div className="grid grid-cols-2 gap-2 text-xs">
                          <div className="p-2 rounded-lg bg-white border border-blue-200/60 flex flex-col">
                            <span className="text-[10px] font-semibold text-slate-500">
                              Patient Share Change
                            </span>
                            <span
                              className={`font-mono text-base font-bold flex items-center gap-1 ${
                                whatIfResult.patientResponsibilityDelta > 0
                                  ? "text-rose-600"
                                  : "text-emerald-600"
                              }`}
                            >
                              {whatIfResult.patientResponsibilityDelta > 0 ? (
                                <TrendingUp className="w-4 h-4" />
                              ) : (
                                <TrendingDown className="w-4 h-4" />
                              )}
                              {whatIfResult.patientResponsibilityDelta > 0 ? "+" : ""}
                              {formatCurrency(whatIfResult.patientResponsibilityDelta)}
                            </span>
                          </div>

                          <div className="p-2 rounded-lg bg-white border border-blue-200/60 flex flex-col">
                            <span className="text-[10px] font-semibold text-slate-500">
                              Insurer Share Change
                            </span>
                            <span
                              className={`font-mono text-base font-bold flex items-center gap-1 ${
                                whatIfResult.insurerContributionDelta >= 0
                                  ? "text-emerald-600"
                                  : "text-rose-600"
                              }`}
                            >
                              {whatIfResult.insurerContributionDelta >= 0 ? "+" : ""}
                              {formatCurrency(whatIfResult.insurerContributionDelta)}
                            </span>
                          </div>
                        </div>
                      </div>

                      {/* Explanation of Changes */}
                      <div className="space-y-1.5">
                        <span className="text-[11px] font-bold uppercase tracking-wider text-slate-500">
                          Why the Estimate Changed:
                        </span>
                        <ul className="space-y-1 text-xs text-slate-700">
                          {whatIfResult.explanationOfChanges.map((exp, idx) => (
                            <li
                              key={idx}
                              className="p-2.5 rounded-lg bg-slate-50 border border-slate-200/70 flex items-start gap-2 text-[11px] leading-relaxed"
                            >
                              <Info className="w-3.5 h-3.5 text-[#0052D1] shrink-0 mt-0.5" />
                              <span>{exp}</span>
                            </li>
                          ))}
                        </ul>
                      </div>
                    </div>
                  ) : (
                    <div className="p-6 text-center text-xs text-slate-500 border border-dashed border-slate-200 rounded-xl">
                      Click &quot;Run What-If Comparison&quot; to see the financial delta.
                    </div>
                  )}
                </CardContent>
              </Card>
            )}
          </div>
        </div>
      </main>
        </>
      )}

      {/* Evidence Inspection Drawer */}
      <EvidenceDrawer
        isOpen={evidenceDrawerOpen}
        onClose={() => setEvidenceDrawerOpen(false)}
        evidence={
          selectedEvidence
            ? {
                id: String(selectedEvidence.id || "ev-1"),
                title: selectedEvidence.clauseSection || "Policy Evidence Clause",
                sourceDoc: selectedEvidence.documentSource || "Care Premier Policy Schedule 2026.pdf",
                clauseReference: selectedEvidence.clauseSection || "Policy Section",
                pageNumber: String(selectedEvidence.page || 1),
                sourceText: selectedEvidence.extractedText || "No excerpt text available.",
                aiInterpretation:
                  selectedEvidence.interpretation ||
                  "Verbatim clause extracted directly from the verified policy document.",
                deterministicRule: "Direct contractual stipulation regarding admissible medical expenses and limits.",
                calculationImpact: "Governs admissibility sub-limit, co-payment, or room-rent penalty threshold.",
                confidence: selectedEvidence.confidence
                  ? Math.round(selectedEvidence.confidence * 100)
                  : 96,
                category: "Policy Rule Citation",
              }
            : null
        }
      />

      <Footer />
    </div>
  );
}

export default function AssistantPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen flex items-center justify-center bg-slate-50">
          <div className="flex flex-col items-center gap-3">
            <RefreshCw className="w-8 h-8 text-[#0052D1] animate-spin" />
            <span className="text-sm font-semibold text-slate-600">
              Loading Policy Assistant...
            </span>
          </div>
        </div>
      }
    >
      <AssistantContent />
    </Suspense>
  );
}
