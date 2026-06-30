/**
 * percentageFormatter.ts
 *
 * Percentage formatting for AskDB.
 * Handles both decimal ratios (0–1) and already-scaled values (0–100).
 */

import { EMPTY_DISPLAY } from "./numberFormatter";

/**
 * formatPercentage
 *
 * Formats a decimal ratio (0–1) as a percentage string.
 *
 * @example
 * formatPercentage(0.8756) → "87.56%"
 * formatPercentage(0.5)    → "50.00%"
 * formatPercentage(null)   → "—"
 */
export function formatPercentage(
  value: unknown,
  decimals = 2,
  locale = "en-IN",
): string {
  if (value === null || value === undefined || value === "") return EMPTY_DISPLAY;
  const n = Number(value);
  if (isNaN(n) || !isFinite(n)) return EMPTY_DISPLAY;

  return new Intl.NumberFormat(locale, {
    style: "percent",
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(n);
}

/**
 * formatPercentageValue
 *
 * Formats an already-scaled percentage value (0–100).
 *
 * @example
 * formatPercentageValue(87.56) → "87.56%"
 * formatPercentageValue(45)    → "45.00%"
 * formatPercentageValue(null)  → "—"
 */
export function formatPercentageValue(
  value: unknown,
  decimals = 2,
  locale = "en-IN",
): string {
  if (value === null || value === undefined || value === "") return EMPTY_DISPLAY;
  const n = Number(value);
  if (isNaN(n) || !isFinite(n)) return EMPTY_DISPLAY;

  // Divide by 100 to use Intl percent style
  return new Intl.NumberFormat(locale, {
    style: "percent",
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(n / 100);
}

/**
 * formatPercentageRaw
 *
 * Returns a simple "X%" string without using Intl style,
 * useful for compact display (e.g. "87.6%", "45%").
 */
export function formatPercentageRaw(value: unknown, decimals = 1): string {
  if (value === null || value === undefined || value === "") return EMPTY_DISPLAY;
  const n = Number(value);
  if (isNaN(n) || !isFinite(n)) return EMPTY_DISPLAY;
  return `${n.toFixed(decimals)}%`;
}
