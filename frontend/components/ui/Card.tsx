import React, { forwardRef } from "react";
import { cn } from "@/lib/utils";
import { DataSourceTier } from "@/types";

export interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  hoverLift?: boolean;
  tier?: DataSourceTier;
  subtle?: boolean;
}

export const Card = forwardRef<HTMLDivElement, CardProps>(
  ({ className, hoverLift = false, tier, subtle = false, children, ...props }, ref) => {
    const tierStyles: Record<DataSourceTier, string> = {
      policy_source: "border-l-4 border-l-[#0052D1] bg-white",
      ai_interpretation: "border-l-4 border-l-[#6366F1] bg-white",
      deterministic_calc: "border-l-4 border-l-[#006B5F] bg-white",
      estimated_result: "border-l-4 border-l-[#D97706] bg-white",
    };

    return (
      <div
        ref={ref}
        className={cn(
          "rounded-2xl border border-slate-200/80 transition-all duration-200",
          subtle ? "bg-[#F8F9FF]" : "bg-white",
          hoverLift && "hover:-translate-y-0.5 hover:shadow-md hover:border-slate-300",
          tier ? tierStyles[tier] : "shadow-[0_1px_3px_rgba(10,29,46,0.04)]",
          className
        )}
        {...props}
      >
        {children}
      </div>
    );
  }
);
Card.displayName = "Card";

export function CardHeader({
  className,
  ...props
}: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn("px-6 py-4 border-b border-slate-100 flex flex-col gap-1.5", className)}
      {...props}
    />
  );
}

export function CardTitle({
  className,
  ...props
}: React.HTMLAttributes<HTMLHeadingElement>) {
  return (
    <h3
      className={cn(
        "text-base font-semibold text-[#0A1D2E] tracking-tight leading-snug",
        className
      )}
      {...props}
    />
  );
}

export function CardDescription({
  className,
  ...props
}: React.HTMLAttributes<HTMLParagraphElement>) {
  return (
    <p
      className={cn("text-xs text-slate-500 leading-relaxed", className)}
      {...props}
    />
  );
}

export function CardContent({
  className,
  ...props
}: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("p-6", className)} {...props} />;
}

export function CardFooter({
  className,
  ...props
}: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn(
        "px-6 py-4 border-t border-slate-100 bg-slate-50/50 rounded-b-2xl flex items-center justify-between gap-4",
        className
      )}
      {...props}
    />
  );
}
