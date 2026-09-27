import React from "react";
import { cn } from "@/lib/utils";
import { Loader2 } from "lucide-react";

export interface LoadingStateProps extends React.HTMLAttributes<HTMLDivElement> {
  message?: string;
  subtext?: string;
  variant?: "spinner" | "skeleton" | "card";
  size?: "sm" | "md" | "lg";
  lines?: number;
}

export function LoadingState({
  message = "Processing intelligence...",
  subtext,
  variant = "spinner",
  size = "md",
  lines = 3,
  className,
  ...props
}: LoadingStateProps) {
  const spinnerSizes = {
    sm: "w-4 h-4",
    md: "w-6 h-6",
    lg: "w-8 h-8",
  };

  if (variant === "skeleton") {
    return (
      <div
        className={cn("w-full space-y-3 animate-pulse", className)}
        role="status"
        aria-label="Loading content"
        {...props}
      >
        <div className="h-6 bg-slate-200 rounded-lg w-1/3" />
        {Array.from({ length: lines }).map((_, i) => (
          <div
            key={i}
            className="h-4 bg-slate-100 rounded-md"
            style={{ width: `${95 - i * 15}%` }}
          />
        ))}
      </div>
    );
  }

  if (variant === "card") {
    return (
      <div
        className={cn(
          "rounded-2xl border border-slate-200 bg-white p-8 flex flex-col items-center justify-center text-center gap-3",
          className
        )}
        role="status"
        aria-live="polite"
        {...props}
      >
        <div className="w-12 h-12 rounded-2xl bg-[#EEF4FF] flex items-center justify-center text-[#0052D1]">
          <Loader2 className={cn(spinnerSizes[size], "animate-spin")} />
        </div>
        <div className="flex flex-col gap-1 max-w-sm">
          <p className="text-sm font-semibold text-[#0A1D2E]">{message}</p>
          {subtext && <p className="text-xs text-slate-500">{subtext}</p>}
        </div>
      </div>
    );
  }

  return (
    <div
      className={cn("flex flex-col items-center justify-center gap-2.5 py-6", className)}
      role="status"
      aria-live="polite"
      {...props}
    >
      <Loader2 className={cn(spinnerSizes[size], "animate-spin text-[#0052D1]")} />
      <span className="text-xs font-medium text-slate-600">{message}</span>
      {subtext && <span className="text-[11px] text-slate-400">{subtext}</span>}
    </div>
  );
}
