/**
 * dateFormatter.ts
 *
 * Centralized date/time formatting for AskDB presentation layer.
 * Handles ISO strings, YYYY-MM-DD, and Date objects.
 * Does not modify any stored or backend data.
 */

import { EMPTY_DISPLAY } from "./numberFormatter";

// ─── Type guard ───────────────────────────────────────────────────────────────

function toDate(value: unknown): Date | null {
  if (value === null || value === undefined || value === "") return null;
  if (value instanceof Date) return isNaN(value.getTime()) ? null : value;
  const d = new Date(String(value));
  return isNaN(d.getTime()) ? null : d;
}

// ─── Formatters ───────────────────────────────────────────────────────────────

/**
 * formatDate
 *
 * Human-friendly relative date (same as existing lib/utils.ts formatDate).
 * Kept here as the canonical implementation; lib/utils.ts re-exports it.
 *
 * @example
 * formatDate("2026-06-30T10:00:00Z") → "Just now" / "3h ago" / "Jun 30, 2026"
 */
export function formatDate(value: unknown): string {
  const date = toDate(value);
  if (!date) return EMPTY_DISPLAY;

  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60_000);
  const diffHours = Math.floor(diffMs / 3_600_000);
  const diffDays = Math.floor(diffMs / 86_400_000);

  if (diffMins < 1) return "Just now";
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays < 7) return `${diffDays}d ago`;

  return date.toLocaleDateString("en-IN", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

/**
 * formatDateShort
 *
 * Short date: "Jun 30, 2026"
 */
export function formatDateShort(value: unknown, locale = "en-IN"): string {
  const date = toDate(value);
  if (!date) return EMPTY_DISPLAY;
  return date.toLocaleDateString(locale, {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

/**
 * formatDateFull
 *
 * Full date: "Monday, 30 June 2026"
 */
export function formatDateFull(value: unknown, locale = "en-IN"): string {
  const date = toDate(value);
  if (!date) return EMPTY_DISPLAY;
  return date.toLocaleDateString(locale, {
    weekday: "long",
    month: "long",
    day: "numeric",
    year: "numeric",
  });
}

/**
 * formatDateISO
 *
 * ISO format without the time component: "2026-06-30"
 */
export function formatDateISO(value: unknown): string {
  const date = toDate(value);
  if (!date) return EMPTY_DISPLAY;
  return date.toISOString().slice(0, 10);
}

/**
 * formatDateTime
 *
 * Date + time: "30 Jun 2026, 08:30 PM"
 */
export function formatDateTime(value: unknown, locale = "en-IN"): string {
  const date = toDate(value);
  if (!date) return EMPTY_DISPLAY;
  return date.toLocaleString(locale, {
    day: "numeric",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

/**
 * formatMs
 *
 * Milliseconds → human-readable duration. "42ms" or "1.23s".
 * Kept here as canonical; lib/utils.ts re-exports it.
 */
export function formatMs(ms: unknown): string {
  if (ms === null || ms === undefined) return EMPTY_DISPLAY;
  const n = Number(ms);
  if (isNaN(n)) return EMPTY_DISPLAY;
  if (n === 0) return "0ms";
  if (n < 1000) return `${n}ms`;
  return `${(n / 1000).toFixed(2)}s`;
}
