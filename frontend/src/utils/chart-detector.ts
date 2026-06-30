import type { ColumnMeta, ColumnKind } from "@/types/chart";

// ─── Date column name hints — EXACT WORD matching only ────────────────────────
//
// CRITICAL: Use word-boundary tokens, not substrings.
// "at" as a substring would match "budget", "date" as a substring matches fine
// but must be an exact segment when split on underscores/camelCase boundaries.
//
// Strategy: split the column name on _ and camelCase boundaries,
// then check if any resulting token exactly matches a date keyword.

const DATE_WORD_TOKENS = new Set([
  "date", "time", "year", "month", "day", "week", "period",
  "created", "updated", "timestamp", "ts", "datetime", "hired", "born",
]);

/** Split a column name into lower-cased word tokens */
function tokenizeColumnName(colName: string): string[] {
  return colName
    .replace(/([a-z])([A-Z])/g, "$1_$2")  // camelCase → snake_case
    .toLowerCase()
    .split(/[_\s\-\.]+/)                   // split on separators
    .filter(Boolean);
}

/** Returns true if the column name contains a date-related word token */
function columnNameIsDateHint(colName: string): boolean {
  const tokens = tokenizeColumnName(colName);
  return tokens.some((t) => DATE_WORD_TOKENS.has(t));
}

// ─── Date value patterns — no false positives on plain numbers ────────────────
//
// REMOVED: /^\d{4}$/ — this matches salary/count values like 2024, 4000, etc.
// Only match genuine date strings.

const DATE_VALUE_PATTERNS = [
  // ISO 8601: 2023-01-15 or 2023-01-15T10:30:00
  /^\d{4}-\d{2}-\d{2}/,
  // DD/MM/YYYY or MM/DD/YYYY (must have at least 5 chars)
  /^\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4}$/,
  // "January 2023", "Jan 2023", "Jan 15 2023"
  /^(january|february|march|april|may|june|july|august|september|october|november|december|jan|feb|mar|apr|jun|jul|aug|sep|oct|nov|dec)\b/i,
];

// ─── Value type detection ─────────────────────────────────────────────────────

function isNumericValue(v: unknown): boolean {
  if (v === null || v === undefined || v === "" || typeof v === "boolean") return false;
  const n = Number(v);
  return !isNaN(n) && isFinite(n);
}

function isDateValue(v: unknown): boolean {
  if (v === null || v === undefined) return false;
  const s = String(v).trim();
  // Must not be a plain number — plain numbers are NOT dates
  if (isNumericValue(s)) return false;
  // Check against strict date patterns
  if (DATE_VALUE_PATTERNS.some((p) => p.test(s))) return true;
  // Last resort: try Date parse, but only for strings with separators
  if (s.includes("-") || s.includes("/") || s.includes(" ")) {
    const d = new Date(s);
    return !isNaN(d.getTime());
  }
  return false;
}

// ─── Column kind resolver ─────────────────────────────────────────────────────

function detectKind(colName: string, samples: unknown[]): ColumnKind {
  const nonNull = samples.filter(
    (v) => v !== null && v !== undefined && v !== "",
  );
  if (nonNull.length === 0) return "unknown";

  const nameHintDate = columnNameIsDateHint(colName);

  const numericCount = nonNull.filter(isNumericValue).length;
  const dateCount    = nonNull.filter(isDateValue).length;
  const numericRatio = numericCount / nonNull.length;
  const dateRatio    = dateCount    / nonNull.length;

  // ── Priority 1: Strong value-based evidence ─────────────────────────────
  if (dateRatio >= 0.8)    return "date";
  if (numericRatio >= 0.7) return "numeric";

  // ── Priority 2: Name hint + moderate value evidence ─────────────────────
  if (nameHintDate && dateRatio >= 0.4) return "date";

  // ── Priority 3: Name hint alone (when values are ambiguous) ─────────────
  // Only apply this when there is no dominant numeric signal
  if (nameHintDate && numericRatio < 0.5) return "date";

  // ── Priority 4: Numeric wins over name hint ──────────────────────────────
  if (numericRatio >= 0.5) return "numeric";

  // ── Priority 5: Low-cardinality strings → category ───────────────────────
  const distinct = new Set(nonNull.map(String));
  if (distinct.size <= 30 && nonNull.length >= 1) return "category";

  return "text";
}

// ─── Public API ───────────────────────────────────────────────────────────────

/**
 * Inspect ONLY the result-set columns and rows passed in.
 * Never reads from schema, ORM, or any other source.
 */
export function detectColumns(
  columnNames: string[],
  rows: Record<string, unknown>[],
): ColumnMeta[] {
  const sampleRows = rows.slice(0, 50);

  return columnNames.map((name): ColumnMeta => {
    const sample = sampleRows
      .map((r) => r[name])
      .filter((v) => v !== null && v !== undefined);

    const distinct = new Set(sample.map(String));
    const kind = detectKind(name, sample);

    // ── Debug logging — remove or gate behind env flag in production ────────
    if (typeof window !== "undefined" && (window as any).__ASKDB_CHART_DEBUG__) {
      console.group(`[ChartDetector] Column: "${name}"`);
      console.log("  Detected kind :", kind);
      console.log("  Sample values :", sample.slice(0, 5));
      console.log("  Distinct count:", distinct.size);
      console.groupEnd();
    }

    return {
      name,
      kind,
      sample: sample.slice(0, 20) as any[],
      isHighCardinality: distinct.size > 20,
      distinctCount: distinct.size,
    };
  });
}

export function getColumnsByKind(
  metas: ColumnMeta[],
  kind: ColumnKind,
): ColumnMeta[] {
  return metas.filter((m) => m.kind === kind);
}
