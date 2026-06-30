import type { ColumnMeta, ColumnKind } from "@/types/chart";

// ─── Date patterns ───────────────────────────────────────────────────────────

const DATE_COLUMN_HINTS = [
  "date", "time", "year", "month", "day", "week", "period",
  "created", "updated", "at", "timestamp", "ts",
];

const DATE_VALUE_PATTERNS = [
  // ISO 8601
  /^\d{4}-\d{2}-\d{2}/,
  // DD/MM/YYYY or MM/DD/YYYY
  /^\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4}/,
  // "January 2023", "Jan 2023"
  /^(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)/i,
  // Pure year
  /^\d{4}$/,
];

// ─── Numeric detection ────────────────────────────────────────────────────────

function isNumericValue(v: any): boolean {
  if (v === null || v === undefined || v === "") return false;
  return !isNaN(Number(v)) && v !== "";
}

function isDateValue(v: any): boolean {
  if (v === null || v === undefined) return false;
  const s = String(v).trim();
  if (DATE_VALUE_PATTERNS.some((p) => p.test(s))) return true;
  const d = new Date(s);
  return !isNaN(d.getTime()) && isNaN(Number(s));
}

// ─── Column kind resolver ────────────────────────────────────────────────────

function detectKind(colName: string, samples: any[]): ColumnKind {
  const lc = colName.toLowerCase();

  // Check column name hints first (fast path)
  const nameHintDate = DATE_COLUMN_HINTS.some((h) => lc.includes(h));

  // Filter non-null samples
  const nonNull = samples.filter((v) => v !== null && v !== undefined && v !== "");
  if (nonNull.length === 0) return "unknown";

  // Numeric check: majority of samples parse as numbers
  const numericCount = nonNull.filter(isNumericValue).length;
  const dateCount = nonNull.filter(isDateValue).length;
  const numericRatio = numericCount / nonNull.length;
  const dateRatio = dateCount / nonNull.length;

  if (nameHintDate && dateRatio >= 0.6) return "date";
  if (dateRatio >= 0.8) return "date";
  if (numericRatio >= 0.8) return "numeric";
  if (nameHintDate) return "date";

  // Category: low-cardinality strings
  const distinct = new Set(nonNull.map(String));
  if (distinct.size <= 20 && nonNull.length >= 2) return "category";

  return "text";
}

// ─── Public API ──────────────────────────────────────────────────────────────

/**
 * Inspect column names and sample rows, returning metadata for each column.
 */
export function detectColumns(
  columnNames: string[],
  rows: Record<string, any>[],
): ColumnMeta[] {
  const sampleRows = rows.slice(0, 30);

  return columnNames.map((name): ColumnMeta => {
    const sample = sampleRows
      .map((r) => r[name])
      .filter((v) => v !== null && v !== undefined);

    const distinct = new Set(sample.map(String));
    const kind = detectKind(name, sample);

    return {
      name,
      kind,
      sample: sample.slice(0, 20),
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
