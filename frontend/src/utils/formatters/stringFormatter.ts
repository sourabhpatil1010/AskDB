/**
 * stringFormatter.ts
 *
 * String presentation utilities for AskDB.
 * Provides title case, sentence case, truncation, and fallback helpers.
 */

import { EMPTY_DISPLAY } from "./numberFormatter";

/**
 * toTitleCase
 *
 * @example  "hello world" → "Hello World"
 */
export function toTitleCase(value: unknown): string {
  if (value === null || value === undefined) return EMPTY_DISPLAY;
  return String(value)
    .toLowerCase()
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

/**
 * toSentenceCase
 *
 * @example  "hello world. how are you" → "Hello world. How are you"
 */
export function toSentenceCase(value: unknown): string {
  if (value === null || value === undefined) return EMPTY_DISPLAY;
  return String(value).replace(/(^\s*\w|[.!?]\s+\w)/g, (c) => c.toUpperCase());
}

/**
 * truncateText
 *
 * Truncates a string at the given character limit, appending "…".
 *
 * @example  truncateText("Hello World", 7) → "Hello W…"
 */
export function truncateText(value: unknown, maxLength = 40): string {
  if (value === null || value === undefined) return EMPTY_DISPLAY;
  const s = String(value);
  return s.length > maxLength ? s.slice(0, maxLength - 1) + "…" : s;
}

/**
 * withFallback
 *
 * Returns the value if non-empty, otherwise the fallback (default "—").
 *
 * @example  withFallback(null)       → "—"
 * @example  withFallback("", "N/A")  → "N/A"
 */
export function withFallback(value: unknown, fallback = EMPTY_DISPLAY): string {
  if (value === null || value === undefined || value === "") return fallback;
  return String(value);
}

/**
 * slugify
 *
 * Converts a label to a URL-safe slug.
 * @example  slugify("Total Queries") → "total-queries"
 */
export function slugify(value: unknown): string {
  return String(value ?? "")
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "");
}

/**
 * formatColumnLabel
 *
 * Converts a SQL column name to a readable display label.
 * @example  formatColumnLabel("avg_salary") → "Avg Salary"
 * @example  formatColumnLabel("departmentID") → "Department I D"  (best-effort)
 */
export function formatColumnLabel(value: unknown): string {
  if (value === null || value === undefined) return EMPTY_DISPLAY;
  return String(value)
    .replace(/_/g, " ")
    .replace(/([a-z])([A-Z])/g, "$1 $2")
    .replace(/\b\w/g, (c) => c.toUpperCase())
    .trim();
}
