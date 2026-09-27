import React from "react";
import { cn } from "@/lib/utils";
import { AlertCircle, RefreshCw } from "lucide-react";
import { Button } from "./Button";

export interface ErrorStateProps extends React.HTMLAttributes<HTMLDivElement> {
  title?: string;
  message: string;
  details?: string;
  onRetry?: () => void;
  retryLabel?: string;
  variant?: "card" | "banner" | "inline";
}

export function ErrorState({
  title = "Unable to process document",
  message,
  details,
  onRetry,
  retryLabel = "Retry Analysis",
  variant = "card",
  className,
  ...props
}: ErrorStateProps) {
  if (variant === "banner") {
    return (
      <div
        className={cn(
          "rounded-xl border border-red-200 bg-[#FEF2F2] p-4 flex items-start gap-3 text-left",
          className
        )}
        role="alert"
        {...props}
      >
        <AlertCircle className="w-5 h-5 text-[#BA1A1A] shrink-0 mt-0.5" />
        <div className="flex-1 min-w-0">
          <p className="text-sm font-semibold text-[#BA1A1A]">{title}</p>
          <p className="text-xs text-red-700 mt-0.5">{message}</p>
        </div>
        {onRetry && (
          <Button
            size="xs"
            variant="outline"
            onClick={onRetry}
            className="border-[#BA1A1A] text-[#BA1A1A] hover:bg-red-50"
          >
            {retryLabel}
          </Button>
        )}
      </div>
    );
  }

  if (variant === "inline") {
    return (
      <div
        className={cn(
          "inline-flex items-center gap-2 text-xs text-[#BA1A1A] bg-red-50 px-3 py-1.5 rounded-lg border border-red-200",
          className
        )}
        role="alert"
        {...props}
      >
        <AlertCircle className="w-4 h-4 shrink-0" />
        <span>{message}</span>
      </div>
    );
  }

  return (
    <div
      className={cn(
        "rounded-2xl border border-red-200 bg-[#FFFDFD] p-8 sm:p-10 flex flex-col items-center justify-center text-center gap-4",
        className
      )}
      role="alert"
      {...props}
    >
      <div className="w-12 h-12 rounded-2xl bg-red-50 border border-red-200 flex items-center justify-center text-[#BA1A1A] shadow-sm">
        <AlertCircle className="w-6 h-6" />
      </div>

      <div className="flex flex-col gap-1 max-w-md">
        <h4 className="text-base font-semibold text-[#BA1A1A]">{title}</h4>
        <p className="text-xs sm:text-sm text-slate-600 leading-relaxed">{message}</p>
        {details && (
          <p className="text-[11px] font-mono text-slate-400 mt-2 bg-slate-50 p-2 rounded border border-slate-200 text-left">
            {details}
          </p>
        )}
      </div>

      {onRetry && (
        <Button
          variant="danger"
          size="sm"
          onClick={onRetry}
          leftIcon={<RefreshCw className="w-3.5 h-3.5" />}
        >
          {retryLabel}
        </Button>
      )}
    </div>
  );
}
