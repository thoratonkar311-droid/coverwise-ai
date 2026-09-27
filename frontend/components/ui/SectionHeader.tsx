import React from "react";
import { cn } from "@/lib/utils";
import { Badge } from "./Badge";

export interface SectionHeaderProps extends React.HTMLAttributes<HTMLDivElement> {
  badge?: string;
  badgeVariant?: "default" | "primary" | "secondary" | "teal" | "outline";
  title: string;
  description?: string;
  align?: "left" | "center";
  actions?: React.ReactNode;
}

export function SectionHeader({
  badge,
  badgeVariant = "default",
  title,
  description,
  align = "left",
  actions,
  className,
  ...props
}: SectionHeaderProps) {
  const isCenter = align === "center";

  return (
    <div
      className={cn(
        "flex flex-col gap-3 mb-8 md:mb-12",
        isCenter ? "items-center text-center" : "items-start text-left",
        actions && "md:flex-row md:items-end md:justify-between",
        className
      )}
      {...props}
    >
      <div
        className={cn(
          "flex flex-col gap-2 max-w-2xl",
          isCenter && "items-center"
        )}
      >
        {badge && (
          <Badge variant={badgeVariant} size="sm" className="w-fit">
            {badge}
          </Badge>
        )}
        <h2 className="text-2xl sm:text-3xl font-bold tracking-tight text-[#0A1D2E] leading-tight">
          {title}
        </h2>
        {description && (
          <p className="text-sm sm:text-base text-slate-600 leading-relaxed">
            {description}
          </p>
        )}
      </div>

      {actions && (
        <div className="flex items-center gap-3 shrink-0 pt-2 md:pt-0">
          {actions}
        </div>
      )}
    </div>
  );
}
