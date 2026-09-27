import React, { forwardRef } from "react";
import { cn } from "@/lib/utils";
import { Loader2 } from "lucide-react";

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?:
    | "primary"
    | "secondary"
    | "teal"
    | "outline"
    | "ghost"
    | "danger"
    | "subtle";
  size?: "xs" | "sm" | "md" | "lg";
  isLoading?: boolean;
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      className,
      variant = "primary",
      size = "md",
      isLoading = false,
      leftIcon,
      rightIcon,
      disabled,
      children,
      ...props
    },
    ref
  ) => {
    const baseStyles =
      "inline-flex items-center justify-center font-medium transition-all duration-200 cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed disabled:pointer-events-none focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 select-none";

    const variantStyles = {
      primary:
        "bg-[#0052D1] hover:bg-[#1769FF] text-white shadow-sm hover:shadow active:scale-[0.99] focus-visible:ring-[#1769FF]",
      secondary:
        "bg-[#0A1D2E] hover:bg-[#152e46] text-white shadow-sm active:scale-[0.99] focus-visible:ring-[#0A1D2E]",
      teal:
        "bg-[#006B5F] hover:bg-[#008575] text-white shadow-sm active:scale-[0.99] focus-visible:ring-[#006B5F]",
      outline:
        "border border-[#0052D1] text-[#0052D1] bg-white hover:bg-[#EEF4FF] active:scale-[0.99] focus-visible:ring-[#0052D1]",
      ghost:
        "text-[#0A1D2E] hover:bg-[#EEF4FF] hover:text-[#0052D1] focus-visible:ring-[#0052D1]",
      danger:
        "bg-[#BA1A1A] hover:bg-[#961414] text-white shadow-sm active:scale-[0.99] focus-visible:ring-[#BA1A1A]",
      subtle:
        "bg-[#EEF4FF] text-[#0052D1] hover:bg-[#dbe7ff] active:scale-[0.99] focus-visible:ring-[#0052D1]",
    };

    const sizeStyles = {
      xs: "text-xs py-1 px-2.5 rounded-lg gap-1.5",
      sm: "text-xs font-semibold py-1.5 px-3 rounded-lg gap-1.5",
      md: "text-sm py-2 px-4 rounded-xl gap-2",
      lg: "text-base py-2.5 px-6 rounded-xl gap-2.5",
    };

    return (
      <button
        ref={ref}
        disabled={disabled || isLoading}
        aria-busy={isLoading}
        className={cn(baseStyles, variantStyles[variant], sizeStyles[size], className)}
        {...props}
      >
        {isLoading ? (
          <Loader2 className="w-4 h-4 animate-spin shrink-0" aria-hidden="true" />
        ) : (
          leftIcon && <span className="inline-flex shrink-0">{leftIcon}</span>
        )}
        <span>{children}</span>
        {!isLoading && rightIcon && (
          <span className="inline-flex shrink-0">{rightIcon}</span>
        )}
      </button>
    );
  }
);

Button.displayName = "Button";
