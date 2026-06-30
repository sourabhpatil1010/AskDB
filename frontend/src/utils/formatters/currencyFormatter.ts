/**
 * currencyFormatter.ts
 *
 * Locale-aware currency formatting for AskDB.
 * Default locale: en-IN (Indian Rupee).
 * The currency symbol is never hardcoded — it comes from Intl.NumberFormat.
 */

import { EMPTY_DISPLAY } from "./numberFormatter";

export type SupportedCurrency = "INR" | "USD" | "EUR" | "GBP" | "JPY" | "AED";

export const CURRENCY_LOCALE_MAP: Record<SupportedCurrency, string> = {
  INR: "en-IN",
  USD: "en-US",
  EUR: "de-DE",
  GBP: "en-GB",
  JPY: "ja-JP",
  AED: "ar-AE",
};

/**
 * formatCurrency
 *
 * Formats a number as currency with the correct symbol and locale grouping.
 *
 * @example
 * formatCurrency(115244.73)             → "₹1,15,244.73"   (INR default)
 * formatCurrency(115244.73, "USD")      → "$115,244.73"
 * formatCurrency(null)                  → "—"
 */
export function formatCurrency(
  value: unknown,
  currency: SupportedCurrency = "INR",
  decimals = 2,
): string {
  if (value === null || value === undefined || value === "") return EMPTY_DISPLAY;
  const n = Number(value);
  if (isNaN(n) || !isFinite(n)) return EMPTY_DISPLAY;

  const locale = CURRENCY_LOCALE_MAP[currency] ?? "en-IN";

  return new Intl.NumberFormat(locale, {
    style: "currency",
    currency,
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(n);
}

/**
 * formatCurrencyCompact
 *
 * Short-form currency for KPI cards and badges.
 *
 * @example
 * formatCurrencyCompact(1_500_000) → "₹15L"  (en-IN compact)
 * formatCurrencyCompact(115244)    → "₹1.2L"
 */
export function formatCurrencyCompact(
  value: unknown,
  currency: SupportedCurrency = "INR",
): string {
  if (value === null || value === undefined || value === "") return EMPTY_DISPLAY;
  const n = Number(value);
  if (isNaN(n) || !isFinite(n)) return EMPTY_DISPLAY;

  const locale = CURRENCY_LOCALE_MAP[currency] ?? "en-IN";

  return new Intl.NumberFormat(locale, {
    style: "currency",
    currency,
    notation: "compact",
    maximumFractionDigits: 1,
  }).format(n);
}
