import type { ChartRecommendation, ChartType } from "@/types/chart";
import { detectColumns, getColumnsByKind } from "@/utils/chart-detector";

// ─── Debug helper ─────────────────────────────────────────────────────────────

function debugLog(
  columns: string[],
  kinds: Record<string, string>,
  xKey: string,
  yKeys: string[],
  chartType: ChartType,
  reason: string,
) {
  if (typeof window !== "undefined" && (window as any).__ASKDB_CHART_DEBUG__) {
    console.group("[ChartRecommendation] Result");
    console.log("  Detected columns :", columns);
    console.log("  Column types     :", kinds);
    console.log("  Selected X Axis  :", xKey);
    console.log("  Selected Y Axis  :", yKeys);
    console.log("  Recommended Chart:", chartType);
    console.log("  Reason           :", reason);
    console.groupEnd();
  }
}

/**
 * ChartRecommendationEngine
 *
 * Pure utility class — inspects ONLY the columns and rows returned by the
 * current SQL query.  Never reads schema, ORM, hidden metadata, or any
 * column that is not present in the response.
 */
export class ChartRecommendationEngine {
  static recommend(
    columnNames: string[],
    rows: Record<string, any>[],
  ): ChartRecommendation {
    if (!columnNames.length || !rows.length) {
      return ChartRecommendationEngine.none("No data available");
    }

    // Detect kinds ONLY from the actual result-set columns
    const metas         = detectColumns(columnNames, rows);
    const dateColumns   = getColumnsByKind(metas, "date");
    const numericColumns = getColumnsByKind(metas, "numeric");
    const categoryColumns = getColumnsByKind(metas, "category");
    const textColumns   = getColumnsByKind(metas, "text");
    const unknownColumns = getColumnsByKind(metas, "unknown");

    // Label columns = category OR text — both work fine as X axis labels
    const labelColumns = [...categoryColumns, ...textColumns];

    // Build a lookup for debug output
    const kindMap = Object.fromEntries(metas.map((m) => [m.name, m.kind]));

    // ── Rule 1: Date + 2+ Metrics → Multi-Line Chart ─────────────────────────
    if (dateColumns.length >= 1 && numericColumns.length >= 2) {
      const xKey  = dateColumns[0].name;
      const yKeys = numericColumns.slice(0, 6).map((c) => c.name);
      const reason = "Date + multiple numerics → Multi-Line";
      debugLog(columnNames, kindMap, xKey, yKeys, "line", reason);
      return {
        chartType: "line",
        xKey,
        yKeys,
        title: `${yKeys.join(", ")} over ${xKey}`,
        description: "Multi-metric trend over time — Line chart recommended",
        confidence: 0.92,
      };
    }

    // ── Rule 2: Date + 1 Metric → Line Chart ─────────────────────────────────
    if (dateColumns.length >= 1 && numericColumns.length === 1) {
      const xKey  = dateColumns[0].name;
      const yKeys = [numericColumns[0].name];
      const reason = "Date + one numeric → Line";
      debugLog(columnNames, kindMap, xKey, yKeys, "line", reason);
      return {
        chartType: "line",
        xKey,
        yKeys,
        title: `${yKeys[0]} over ${xKey}`,
        description: "Time-series data — Line chart recommended",
        confidence: 0.95,
      };
    }

    // ── Rule 3: 1+ Labels + 3+ Numerics → Grouped Bar ────────────────────────
    if (labelColumns.length >= 1 && numericColumns.length >= 3) {
      const xKey  = labelColumns[0].name;
      const yKeys = numericColumns.slice(0, 6).map((c) => c.name);
      const reason = "Label + 3+ numerics → Grouped Bar";
      debugLog(columnNames, kindMap, xKey, yKeys, "bar", reason);
      return {
        chartType: "bar",
        xKey,
        yKeys,
        title: `Multiple metrics by ${xKey}`,
        description: "Multi-metric grouped data — Grouped Bar chart recommended",
        confidence: 0.85,
      };
    }

    // ── Rule 4: 3+ Numerics (no label) → Radar ───────────────────────────────
    if (numericColumns.length >= 3 && labelColumns.length === 0) {
      const xKey  = columnNames[0];
      const yKeys = numericColumns.slice(0, 8).map((c) => c.name);
      const reason = "3+ numerics, no label → Radar";
      debugLog(columnNames, kindMap, xKey, yKeys, "radar", reason);
      return {
        chartType: "radar",
        xKey,
        yKeys,
        title: "Multi-metric comparison",
        description: "Multiple numeric metrics — Radar chart recommended",
        confidence: 0.78,
      };
    }

    // ── Rule 5: Exactly 2 Numerics + No Labels → Scatter ─────────────────────
    if (numericColumns.length === 2 && labelColumns.length === 0) {
      const xKey  = numericColumns[0].name;
      const yKeys = [numericColumns[1].name];
      const reason = "Two numerics, no label → Scatter";
      debugLog(columnNames, kindMap, xKey, yKeys, "scatter", reason);
      return {
        chartType: "scatter",
        xKey,
        yKeys,
        title: `${xKey} vs ${yKeys[0]}`,
        description: "Two numeric dimensions — Scatter Plot recommended",
        confidence: 0.88,
      };
    }

    // ── Rule 6: 1+ Labels + 1 Numeric → Bar or Pie ───────────────────────────
    //
    // This is the PRIMARY rule for "Show all departments" style queries:
    //   NAME (text/category) + BUDGET (numeric) → Bar chart
    //
    if (labelColumns.length >= 1 && numericColumns.length === 1) {
      const xCol = labelColumns[0];
      const yCol = numericColumns[0];

      // Prefer Pie only for very small, low-cardinality categorical datasets
      const isPieCandidate =
        rows.length <= 8 &&
        !xCol.isHighCardinality &&
        xCol.distinctCount <= 8;

      const chartType: ChartType = isPieCandidate ? "pie" : "bar";
      const reason = isPieCandidate
        ? `Label + 1 numeric, ≤8 rows → Pie`
        : `Label + 1 numeric → Bar`;

      debugLog(columnNames, kindMap, xCol.name, [yCol.name], chartType, reason);
      return {
        chartType,
        xKey: xCol.name,
        yKeys: [yCol.name],
        title: `${yCol.name} by ${xCol.name}`,
        description: isPieCandidate
          ? "Proportional data — Pie chart recommended"
          : "Categorical comparison — Bar chart recommended",
        confidence: 0.90,
      };
    }

    // ── Rule 7: 2 Numerics with a Label → Bar (X=label, Y=first numeric) ─────
    if (labelColumns.length >= 1 && numericColumns.length === 2) {
      const xKey  = labelColumns[0].name;
      const yKeys = numericColumns.map((c) => c.name);
      const reason = "Label + 2 numerics → Grouped Bar";
      debugLog(columnNames, kindMap, xKey, yKeys, "bar", reason);
      return {
        chartType: "bar",
        xKey,
        yKeys,
        title: `${yKeys.join(" & ")} by ${xKey}`,
        description: "Two-metric comparison — Grouped Bar chart recommended",
        confidence: 0.82,
      };
    }

    // ── Rule 8: Single numeric, use first column as X ─────────────────────────
    if (numericColumns.length === 1) {
      // Try to find any non-numeric column to use as label
      const nonNumericCols = metas.filter(
        (m) => m.kind !== "numeric" && m.kind !== "unknown",
      );
      const xKey  = nonNumericCols.length > 0 ? nonNumericCols[0].name : columnNames[0];
      const yKeys = [numericColumns[0].name];
      const reason = "Single numeric → Bar (best-effort label)";
      debugLog(columnNames, kindMap, xKey, yKeys, "bar", reason);
      return {
        chartType: "bar",
        xKey,
        yKeys,
        title: numericColumns[0].name,
        description: "Numeric distribution — Bar chart recommended",
        confidence: 0.65,
      };
    }

    // ── Fallback ──────────────────────────────────────────────────────────────
    const reason = "No suitable pattern found";
    debugLog(columnNames, kindMap, "", [], "none", reason);
    return ChartRecommendationEngine.none(
      "Dataset doesn't match any visualization pattern",
    );
  }

  private static none(reason: string): ChartRecommendation {
    return {
      chartType: "none",
      xKey: "",
      yKeys: [],
      title: "",
      description: reason,
      confidence: 0,
    };
  }
}
