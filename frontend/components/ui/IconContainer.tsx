import React from "react";
import { cn } from "@/lib/utils";

export interface IconContainerProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?:
    | "primary"
    | "brightBlue"
    | "teal"
    | "navy"
    | "amber"
    | "emerald"
    | "rose"
    | "neutral";
  size?: "xs" | "sm" | "md" | "lg" | "xl";
  shape?: "circle" | "rounded";
}

export function IconContainer({
  className,
  variant = "primary",
  size = "md",
  shape = "rounded",
  children,
  ...props
}: IconContainerProps) {
  const variantStyles = {
    primary: "bg-[#EEF4FF] text-[#0052D1] border border-blue-100",
    brightBlue: "bg-[#1769FF]/10 text-[#1769FF] border border-[#1769FF]/20",
    teal: "bg-[#E6F7F5] text-[#006B5F] border border-teal-100",
    navy: "bg-[#0A1D2E] text-white border border-[#0A1D2E]",
    amber: "bg-[#FFFBEB] text-[#D97706] border border-amber-200/60",
    emerald: "bg-[#ECFDF5] text-[#059669] border border-emerald-100",
    rose: "bg-[#FEF2F2] text-[#BA1A1A] border border-red-100",
    neutral: "bg-slate-100 text-slate-700 border border-slate-200",
  };

  const sizeStyles = {
    xs: "w-7 h-7 p-1 text-xs",
    sm: "w-8 h-8 p-1.5 text-sm",
    md: "w-10 h-10 p-2 text-base",
    lg: "w-12 h-12 p-2.5 text-lg",
    xl: "w-14 h-14 p-3 text-xl",
  };

  const shapeStyles = {
    circle: "rounded-full",
    rounded: "rounded-xl",
  };

  return (
    <div
      className={cn(
        "inline-flex items-center justify-center shrink-0 transition-colors",
        variantStyles[variant],
        sizeStyles[size],
        shapeStyles[shape],
        className
      )}
      {...props}
    >
      {children}
    </div>
  );
}
