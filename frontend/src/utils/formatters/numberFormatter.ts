/**
 * numberFormatter.ts
 *
 * Centralized numeric formatting for the AskDB presentation layer.
 * All functions use Intl.NumberFormat for correct locale-aware output.
 * NEVER call these functions outside the presentation layer.
 * NEVER modify backend responses or stored data.
 */

/** Sentinel returned for invalid / empty values */
export const EMPTY_DISPLAY = "—";

/** Detect whether a value is a meaningful number */
function isValidNumber(value: unknown): value is number {
  if (value === null || value === undefined || value === "") return false;
  const n = Number(value);
  return !isNaN(n) && isFinite(n);
}

// ─── Core formatters ──────────────────────────────────────────────────────────

/**
 * formatNumber
 *
 * General-purpose number formatter.
 * - Adds thousands separators
 * - Rounds to 2 decimal places when fractional
 * - Handles null / undefined / NaN → "—"
 *
 * @example
 * formatNumber(115244.730356) → "1,15,244.73"  (en-IN locale)
 * formatNumber(1245)          → "1,245"
 * formatNumber(0)             → "0"
 * formatNumber(null)          → "—"
 */
export function formatNumber(value: unknown, locale = "en-IN"): string {
  if (!isValidNumber(value)) return EMPTY_DISPLAY;
  const n = Number(value);

  // Integer — no decimal places
  if (Number.isInteger(n)) {
    return new Intl.NumberFormat(locale).format(n);
  }

  // Fractional — 2 decimal places
  return new Intl.NumberFormat(locale, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(n);
}

/**
 * formatInteger
 *
 * Force display as a whole number (no decimals, thousands-separated).
 *
 * @example
 * formatInteger(115244.9)  → "1,15,245"
 * formatInteger(1245)      → "1,245"
 */
export function formatInteger(value: unknown, locale = "en-IN"): string {
  if (!isValidNumber(value)) return EMPTY_DISPLAY;
  return new Intl.NumberFormat(locale, {
    maximumFractionDigits: 0,
  }).format(Math.round(Number(value)));
}

/**
 * formatDecimal
 *
 * Force display with a specific number of decimal places.
 *
 * @example
 * formatDecimal(115244.730356, 4) → "1,15,244.7304"
 */
export function formatDecimal(
  value: unknown,
  decimalPlaces = 2,
  locale = "en-IN",
): string {
  if (!isValidNumber(value)) return EMPTY_DISPLAY;
  return new Intl.NumberFormat(locale, {
    minimumFractionDigits: decimalPlaces,
    maximumFractionDigits: decimalPlaces,
  }).format(Number(value));
}

/**
 * formatCompactNumber
 *
 * Human-readable compact form for axis ticks, KPI cards, badges.
 * Uses K / M / B suffixes.  Falls back to formatNumber for small values.
 *
 * @example
 * formatCompactNumber(1_500_000) → "1.5M"
 * formatCompactNumber(1_245)     → "1.2K"
 * formatCompactNumber(345)       → "345"
 */
export function formatCompactNumber(value: unknown): string {
  if (!isValidNumber(value)) return EMPTY_DISPLAY;
  const n = Number(value);
  const abs = Math.abs(n);
  const sign = n < 0 ? "−" : "";

  if (abs >= 1_000_000_000) return `${sign}${(abs / 1_000_000_000).toFixed(1)}B`;
  if (abs >= 1_000_000)     return `${sign}${(abs / 1_000_000).toFixed(1)}M`;
  if (abs >= 1_000)         return `${sign}${(abs / 1_000).toFixed(1)}K`;
  if (!Number.isInteger(n)) return formatDecimal(n, 2);
  return formatInteger(n);
}

/**
 * smartFormatNumber
 *
 * Inspects the magnitude of a value and picks the best formatter automatically.
 * Ideal for table cells where you don't know the domain ahead of time.
 *
 * - Integer  → thousands-separated, no decimals
 * - Small float (< 1000) → 2 decimal places
 * - Large float → thousands-separated, 2 decimal places
 */
export function smartFormatNumber(value: unknown, locale = "en-IN"): string {
  if (!isValidNumber(value)) return EMPTY_DISPLAY;
  const n = Number(value);
  return formatNumber(n, locale);
}
