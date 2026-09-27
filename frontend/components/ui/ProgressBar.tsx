import React from "react";
import { cn } from "@/lib/utils";

export interface ProgressBarProps extends React.HTMLAttributes<HTMLDivElement> {
  value: number;
  max?: number;
  variant?: "primary" | "teal" | "amber" | "gradient" | "navy";
  size?: "xs" | "sm" | "md" | "lg";
  label?: string;
  showValue?: boolean;
  valueFormatter?: (value: number, max: number) => string;
}

export function ProgressBar({
  value,
  max = 100,
  variant = "primary",
  size = "md",
  label,
  showValue = false,
  valueFormatter,
  className,
  ...props
}: ProgressBarProps) {
  const percentage = Math.min(Math.max((value / max) * 100, 0), 100);

  const variantStyles = {
    primary: "bg-[#0052D1]",
    teal: "bg-[#006B5F]",
    amber: "bg-[#D97706]",
    gradient: "bg-gradient-to-r from-[#006B5F] via-[#0052D1] to-[#1769FF]",
    navy: "bg-[#0A1D2E]",
  };

  const sizeStyles = {
    xs: "h-1 rounded-full",
    sm: "h-1.5 rounded-full",
    md: "h-2.5 rounded-full",
    lg: "h-4 rounded-xl",
  };

  const displayValue = valueFormatter
    ? valueFormatter(value, max)
    : `${Math.round(percentage)}%`;

  return (
    <div className={cn("w-full flex flex-col gap-1.5", className)} {...props}>
      {(label || showValue) && (
        <div className="flex items-center justify-between text-xs text-slate-600 font-medium">
          {label && <span>{label}</span>}
          {showValue && <span className="font-mono text-slate-800">{displayValue}</span>}
        </div>
      )}

      <div
        className={cn(
          "w-full bg-slate-100 overflow-hidden relative",
          sizeStyles[size]
        )}
        role="progressbar"
        aria-valuenow={value}
        aria-valuemin={0}
        aria-valuemax={max}
        aria-label={label || "Progress"}
      >
        <div
          className={cn(
            "h-full transition-all duration-500 ease-out rounded-full",
            variantStyles[variant]
          )}
          style={{ width: `${percentage}%` }}
        />
      </div>
    </div>
  );
}
