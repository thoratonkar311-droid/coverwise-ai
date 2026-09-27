import React from "react";
import { cn } from "@/lib/utils";
import {
  FileText,
  Sparkles,
  Calculator,
  AlertCircle,
  CheckCircle2,
  HelpCircle,
  AlertTriangle,
  XCircle,
} from "lucide-react";
import { StatusVariant } from "@/types";

export interface StatusBadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant: StatusVariant;
  label?: string;
  showIcon?: boolean;
  size?: "xs" | "sm" | "md";
}

const statusConfig: Record<
  StatusVariant,
  {
    bg: string;
    text: string;
    border: string;
    defaultLabel: string;
    icon: React.ComponentType<{ className?: string }>;
  }
> = {
  policy_source: {
    bg: "bg-[#EEF4FF]",
    text: "text-[#0043AA]",
    border: "border-blue-200",
    defaultLabel: "Policy Source",
    icon: FileText,
  },
  ai_interpretation: {
    bg: "bg-[#F5F3FF]",
    text: "text-[#6B21A8]",
    border: "border-purple-200",
    defaultLabel: "AI Interpretation",
    icon: Sparkles,
  },
  deterministic_calc: {
    bg: "bg-[#E6F7F5]",
    text: "text-[#006B5F]",
    border: "border-emerald-200",
    defaultLabel: "Deterministic Engine",
    icon: Calculator,
  },
  estimated: {
    bg: "bg-[#FFFBEB]",
    text: "text-[#92400E]",
    border: "border-amber-200",
    defaultLabel: "Patient Estimate",
    icon: AlertCircle,
  },
  estimated_result: {
    bg: "bg-[#FFFBEB]",
    text: "text-[#92400E]",
    border: "border-amber-200",
    defaultLabel: "Patient Estimate",
    icon: AlertCircle,
  },
  covered: {
    bg: "bg-[#ECFDF5]",
    text: "text-[#065F46]",
    border: "border-emerald-200",
    defaultLabel: "Potential Coverage",
    icon: CheckCircle2,
  },
  partial: {
    bg: "bg-[#EFF6FF]",
    text: "text-[#1E40AF]",
    border: "border-blue-200",
    defaultLabel: "Partial Coverage (Co-Pay)",
    icon: HelpCircle,
  },
  not_determined: {
    bg: "bg-slate-100",
    text: "text-slate-700",
    border: "border-slate-200",
    defaultLabel: "Not Determined",
    icon: HelpCircle,
  },
  warning: {
    bg: "bg-[#FFF7ED]",
    text: "text-[#C2410C]",
    border: "border-orange-200",
    defaultLabel: "Clause Caveat",
    icon: AlertTriangle,
  },
  error: {
    bg: "bg-[#FEF2F2]",
    text: "text-[#991B1B]",
    border: "border-red-200",
    defaultLabel: "Excluded / Not Covered",
    icon: XCircle,
  },
  neutral: {
    bg: "bg-slate-50",
    text: "text-slate-600",
    border: "border-slate-200",
    defaultLabel: "Informational",
    icon: HelpCircle,
  },
};

export function StatusBadge({
  variant,
  label,
  showIcon = true,
  size = "sm",
  className,
  ...props
}: StatusBadgeProps) {
  const config = statusConfig[variant] || statusConfig.neutral;
  const displayLabel = label || config.defaultLabel;
  const Icon = config.icon;

  const sizeClasses = {
    xs: "text-[11px] py-0.5 px-2 gap-1 rounded-md",
    sm: "text-xs py-1 px-2.5 gap-1.5 rounded-lg",
    md: "text-xs font-semibold py-1 px-3 gap-2 rounded-lg",
  };

  const iconSizes = {
    xs: "w-3 h-3",
    sm: "w-3.5 h-3.5",
    md: "w-4 h-4",
  };

  return (
    <span
      className={cn(
        "inline-flex items-center font-medium border select-none transition-colors",
        config.bg,
        config.text,
        config.border,
        sizeClasses[size],
        className
      )}
      {...props}
    >
      {showIcon && <Icon className={cn(iconSizes[size], "shrink-0")} />}
      <span className="truncate">{displayLabel}</span>
    </span>
  );
}
