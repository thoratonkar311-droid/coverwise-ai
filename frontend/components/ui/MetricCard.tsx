import React from "react";
import { cn } from "@/lib/utils";
import { DataSourceTier } from "@/types";
import { StatusBadge } from "./StatusBadge";
import { ArrowUpRight, ArrowDownRight, Minus } from "lucide-react";

export interface MetricCardProps extends React.HTMLAttributes<HTMLDivElement> {
  label: string;
  value: string | number;
  subtext?: string;
  sourceTier?: DataSourceTier;
  sourceLabel?: string;
  icon?: React.ReactNode;
  trend?: {
    direction: "up" | "down" | "neutral";
    text: string;
  };
  highlight?: boolean;
  tier?: DataSourceTier;
  caption?: string;
}

export function MetricCard({
  label,
  value,
  subtext,
  sourceTier,
  sourceLabel,
  icon,
  trend,
  highlight = false,
  caption,
  className,
  ...props
}: MetricCardProps) {
  const trendConfig = {
    up: {
      color: "text-emerald-700 bg-emerald-50 border-emerald-200",
      icon: ArrowUpRight,
    },
    down: {
      color: "text-blue-700 bg-blue-50 border-blue-200",
      icon: ArrowDownRight,
    },
    neutral: {
      color: "text-slate-600 bg-slate-100 border-slate-200",
      icon: Minus,
    },
  };

  return (
    <div
      className={cn(
        "rounded-2xl border p-5 transition-all duration-200 bg-white relative overflow-hidden group",
        highlight
          ? "border-[#0052D1]/40 shadow-[0_4px_20px_rgba(0,82,209,0.08)] ring-1 ring-[#0052D1]/20"
          : "border-slate-200/80 shadow-[0_1px_3px_rgba(10,29,46,0.04)] hover:shadow-md hover:border-slate-300",
        className
      )}
      {...props}
    >
      {/* Top row: Label, Icon, and Source Tier Badge */}
      <div className="flex items-start justify-between gap-3 mb-3">
        <div className="flex flex-col gap-1 min-w-0">
          <span className="text-xs font-semibold uppercase tracking-wider text-slate-500 truncate">
            {label}
          </span>
          {sourceTier && (
            <div className="mt-0.5">
              <StatusBadge
                variant={sourceTier}
                label={sourceLabel}
                size="xs"
                className="font-normal"
              />
            </div>
          )}
        </div>

        {icon && (
          <div className="p-2 rounded-xl bg-slate-50 text-slate-600 group-hover:bg-[#EEF4FF] group-hover:text-[#0052D1] transition-colors shrink-0">
            {icon}
          </div>
        )}
      </div>

      {/* Metric Value: Monospace styling for financial precision */}
      <div className="flex items-baseline gap-2 my-2">
        <span className="font-mono text-2xl sm:text-3xl font-bold tracking-tight text-[#0A1D2E] tabular-nums">
          {value}
        </span>
      </div>

      {/* Subtext and Trend Indicator */}
      {(subtext || trend || caption) && (
        <div className="pt-2 mt-2 border-t border-slate-100 flex items-center justify-between gap-2 text-xs">
          {subtext && (
            <span className="text-slate-500 text-xs truncate flex-1" title={subtext}>
              {subtext}
            </span>
          )}

          {trend && (
            <span
              className={cn(
                "inline-flex items-center gap-1 font-mono text-[11px] px-1.5 py-0.5 rounded border shrink-0",
                trendConfig[trend.direction].color
              )}
            >
              {React.createElement(trendConfig[trend.direction].icon, {
                className: "w-3 h-3",
              })}
              {trend.text}
            </span>
          )}
        </div>
      )}
    </div>
  );
}
