import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

/**
 * Merges class names safely with Tailwind merge support.
 */
export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs));
}

/**
 * Format currency with deterministic two decimal places or rounded integers.
 * If amount is null or undefined, returns "Not Determined" to avoid inventing values.
 */
export function formatCurrency(
  amount: number | null | undefined,
  options?: { currency?: string; decimals?: number; fallback?: string }
): string {
  const { currency = "₹", decimals = 0, fallback = "Not Determined" } = options || {};

  if (amount === null || amount === undefined || isNaN(amount)) {
    return fallback;
  }

  const formatted = new Intl.NumberFormat("en-IN", {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(amount);

  return `${currency}${formatted}`;
}

/**
 * Format percentage string safely.
 * If value is null or undefined, returns "Not Determined".
 */
export function formatPercentage(
  value: number | null | undefined,
  decimals: number = 0,
  fallback: string = "Not Determined"
): string {
  if (value === null || value === undefined || isNaN(value)) {
    return fallback;
  }
  return `${value.toFixed(decimals)}%`;
}

/**
 * Ensures missing text or values are presented transparently as "Not Determined".
 */
export function displayValueOrNotDetermined(
  val: string | number | null | undefined,
  prefix: string = "",
  suffix: string = ""
): string {
  if (val === null || val === undefined || val === "") {
    return "Not Determined";
  }
  return `${prefix}${val}${suffix}`;
}
