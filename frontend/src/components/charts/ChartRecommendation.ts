import type { ChartRecommendation, ChartType } from "@/types/chart";
import { detectColumns, getColumnsByKind } from "@/utils/chart-detector";

/**
 * ChartRecommendationEngine
 *
 * Pure utility class — inspects column metadata + rows and returns the most
 * appropriate ChartRecommendation.  No state, no side effects.
 */
export class ChartRecommendationEngine {
  static recommend(
    columnNames: string[],
    rows: Record<string, any>[],
  ): ChartRecommendation {
    if (!columnNames.length || !rows.length) {
      return ChartRecommendationEngine.none("No data available");
    }

    const metas = detectColumns(columnNames, rows);
    const dateColumns = getColumnsByKind(metas, "date");
    const numericColumns = getColumnsByKind(metas, "numeric");
    const categoryColumns = getColumnsByKind(metas, "category");
    const textColumns = getColumnsByKind(metas, "text");

    // All category/text columns (either kind works as labels)
    const labelColumns = [...categoryColumns, ...textColumns];

    // ── Rule 1: Date + Multiple Metrics → Multi-Line Chart ───────────────────
    if (dateColumns.length >= 1 && numericColumns.length >= 2) {
      return {
        chartType: "line",
        xKey: dateColumns[0].name,
        yKeys: numericColumns.slice(0, 6).map((c) => c.name),
        title: `${numericColumns.map((c) => c.name).join(", ")} over ${dateColumns[0].name}`,
        description: "Multi-metric trend over time — Line chart recommended",
        confidence: 0.92,
      };
    }

    // ── Rule 2: Date + One Metric → Line Chart ───────────────────────────────
    if (dateColumns.length >= 1 && numericColumns.length === 1) {
      return {
        chartType: "line",
        xKey: dateColumns[0].name,
        yKeys: [numericColumns[0].name],
        title: `${numericColumns[0].name} over ${dateColumns[0].name}`,
        description: "Time-series data — Line chart recommended",
        confidence: 0.95,
      };
    }

    // ── Rule 3: Two Numeric → Scatter Plot ───────────────────────────────────
    if (numericColumns.length === 2 && labelColumns.length === 0) {
      return {
        chartType: "scatter",
        xKey: numericColumns[0].name,
        yKeys: [numericColumns[1].name],
        title: `${numericColumns[0].name} vs ${numericColumns[1].name}`,
        description: "Two numeric dimensions — Scatter Plot recommended",
        confidence: 0.88,
      };
    }

    // ── Rule 4: More than 3 Numeric → Radar or Grouped Bar ──────────────────
    if (numericColumns.length >= 3) {
      const hasLabel = labelColumns.length > 0;
      if (hasLabel) {
        // Grouped bar is more readable with a label axis
        return {
          chartType: "bar",
          xKey: labelColumns[0].name,
          yKeys: numericColumns.slice(0, 6).map((c) => c.name),
          title: `Multiple metrics by ${labelColumns[0].name}`,
          description: "Multi-metric grouped data — Grouped Bar chart recommended",
          confidence: 0.85,
        };
      }
      // No label — use radar for multi-metric profiles
      return {
        chartType: "radar",
        xKey: numericColumns[0].name,
        yKeys: numericColumns.slice(0, 8).map((c) => c.name),
        title: "Multi-metric comparison",
        description: "Multiple numeric metrics — Radar chart recommended",
        confidence: 0.78,
      };
    }

    // ── Rule 5: Category + Count/Numeric → Pie (≤12 rows) else Bar ──────────
    if (labelColumns.length >= 1 && numericColumns.length === 1) {
      const xCol = labelColumns[0];
      const yCol = numericColumns[0];
      const rowCount = rows.length;

      const isPieCandidate =
        rowCount <= 12 &&
        !xCol.isHighCardinality &&
        xCol.distinctCount <= 12;

      const chartType: ChartType = isPieCandidate ? "pie" : "bar";
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

    // ── Rule 6: Two text/category columns → Horizontal bar ──────────────────
    if (numericColumns.length === 1 && labelColumns.length >= 1) {
      return {
        chartType: "horizontal-bar",
        xKey: labelColumns[0].name,
        yKeys: [numericColumns[0].name],
        title: `${numericColumns[0].name} by ${labelColumns[0].name}`,
        description: "Ranked comparison — Horizontal Bar chart recommended",
        confidence: 0.80,
      };
    }

    // ── Rule 7: Single numeric column (no labels) → Bar ─────────────────────
    if (numericColumns.length === 1) {
      return {
        chartType: "bar",
        xKey: columnNames[0],
        yKeys: [numericColumns[0].name],
        title: numericColumns[0].name,
        description: "Numeric distribution — Bar chart recommended",
        confidence: 0.65,
      };
    }

    // ── Fallback: No suitable visualization ─────────────────────────────────
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
