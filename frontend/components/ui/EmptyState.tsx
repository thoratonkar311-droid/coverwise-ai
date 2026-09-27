import React from "react";
import { cn } from "@/lib/utils";
import { FileSearch } from "lucide-react";
import { Button } from "./Button";

export interface EmptyStateProps extends React.HTMLAttributes<HTMLDivElement> {
  icon?: React.ReactNode;
  title: string;
  description: string;
  action?: React.ReactNode;
  actionLabel?: string;
  onAction?: () => void;
  compact?: boolean;
}

export function EmptyState({
  icon,
  title,
  description,
  action,
  actionLabel,
  onAction,
  compact = false,
  className,
  ...props
}: EmptyStateProps) {
  return (
    <div
      className={cn(
        "rounded-2xl border border-dashed border-slate-300 bg-white/60 flex flex-col items-center justify-center text-center",
        compact ? "p-6 gap-3" : "p-10 sm:p-14 gap-4",
        className
      )}
      {...props}
    >
      <div className="w-12 h-12 rounded-2xl bg-slate-100 flex items-center justify-center text-slate-500 shadow-inner">
        {icon || <FileSearch className="w-6 h-6" />}
      </div>

      <div className="flex flex-col gap-1 max-w-md">
        <h4 className="text-base font-semibold text-[#0A1D2E]">{title}</h4>
        <p className="text-xs sm:text-sm text-slate-500 leading-relaxed">
          {description}
        </p>
      </div>

      {action ? (
        <div className="mt-2">{action}</div>
      ) : actionLabel && onAction ? (
        <div className="mt-2">
          <Button variant="primary" size="sm" onClick={onAction}>
            {actionLabel}
          </Button>
        </div>
      ) : null}
    </div>
  );
}
