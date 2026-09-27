import React from "react";
import { cn } from "@/lib/utils";

export interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?:
    | "default"
    | "primary"
    | "secondary"
    | "teal"
    | "outline"
    | "neutral"
    | "subtle";
  size?: "xs" | "sm" | "md";
  dot?: boolean;
}

export function Badge({
  className,
  variant = "default",
  size = "sm",
  dot = false,
  children,
  ...props
}: BadgeProps) {
  const variantStyles = {
    default: "bg-[#EEF4FF] text-[#0052D1] border border-blue-200/60",
    primary: "bg-[#0052D1] text-white",
    secondary: "bg-[#0A1D2E] text-white",
    teal: "bg-[#E6F7F5] text-[#006B5F] border border-teal-200/60",
    outline: "border border-slate-300 text-slate-700 bg-white",
    neutral: "bg-slate-100 text-slate-700 border border-slate-200",
    subtle: "bg-slate-50 text-slate-600 border border-slate-200/60",
  };

  const sizeStyles = {
    xs: "text-[10px] font-semibold px-2 py-0.5 rounded-full gap-1 tracking-wide uppercase",
    sm: "text-xs font-medium px-2.5 py-0.5 rounded-full gap-1.5",
    md: "text-xs font-semibold px-3 py-1 rounded-full gap-2",
  };

  return (
    <span
      className={cn(
        "inline-flex items-center select-none font-medium leading-none",
        variantStyles[variant],
        sizeStyles[size],
        className
      )}
      {...props}
    >
      {dot && (
        <span
          className="w-1.5 h-1.5 rounded-full bg-current shrink-0 opacity-80"
          aria-hidden="true"
        />
      )}
      {children}
    </span>
  );
}
