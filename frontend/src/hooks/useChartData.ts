import { useMemo, useState, useEffect, useRef } from "react";
import type { ChartConfig, ChartType } from "@/types/chart";
import { ChartRecommendationEngine } from "@/components/charts/ChartRecommendation";

interface UseChartDataInput {
  columns: string[];
  rows: Record<string, any>[];
}

interface UseChartDataResult {
  chartConfig: ChartConfig | null;
  activeChartType: ChartType;
  setChartType: (type: ChartType) => void;
  hasVisualization: boolean;
  recommendedType: ChartType;
}

/**
 * useChartData
 *
 * Memoizes chart data transformation from existing query results.
 * NEVER executes any new SQL or API calls.
 * Exposes state for user-driven chart type switching.
 *
 * Bug fix: resets user chart type override whenever the dataset
 * changes (new query executed), so stale user preferences from the
 * previous query don't pollute the new result.
 */
export function useChartData({ columns, rows }: UseChartDataInput): UseChartDataResult {
  // Track the "dataset identity" — when columns change, it means a new query
  // was executed and we must reset the user override.
  const prevColumnsKey = useRef<string>("");
  const columnsKey = columns.join("|");

  // User can override the AI-recommended chart type
  const [userChartType, setUserChartType] = useState<ChartType | null>(null);

  // Reset user override whenever the result-set columns change
  useEffect(() => {
    if (prevColumnsKey.current !== columnsKey) {
      prevColumnsKey.current = columnsKey;
      setUserChartType(null);
    }
  }, [columnsKey]);

  // Run recommendation engine — memoized on columns/rows identity
  const recommendation = useMemo(() => {
    if (!columns.length || !rows.length) return null;
    return ChartRecommendationEngine.recommend(columns, rows);
  }, [columns, rows]);

  const recommendedType: ChartType = recommendation?.chartType ?? "none";

  // Active chart type: user override wins, otherwise use AI recommendation
  const activeChartType: ChartType = userChartType ?? recommendedType;

  // Build chart-ready data — memoized, uses ONLY columns/rows from the result
  const chartConfig = useMemo((): ChartConfig | null => {
    if (!recommendation || recommendation.chartType === "none") return null;

    const { xKey, yKeys, title, description } = recommendation;
    const effectiveChartType = userChartType ?? recommendation.chartType;

    // Guard: xKey and yKeys must actually exist in the result columns
    const validXKey   = columns.includes(xKey) ? xKey : columns[0];
    const validYKeys  = yKeys.filter((k) => columns.includes(k));
    if (validYKeys.length === 0) return null;

    // ── Scatter: reshape to { x, y } ────────────────────────────────────────
    if (effectiveChartType === "scatter") {
      const data = rows.map((row) => ({
        x: Number(row[validXKey]) || 0,
        y: Number(row[validYKeys[0]]) || 0,
      }));
      return {
        chartType: effectiveChartType,
        xKey: "x",
        yKeys: ["y"],
        title,
        description,
        data,
      };
    }

    // ── Radar: reshape to { subject, [metric]: value } ───────────────────────
    if (effectiveChartType === "radar") {
      const data = rows.map((row) => {
        const obj: Record<string, any> = {
          subject: String(row[validXKey] ?? row[columns[0]] ?? ""),
        };
        validYKeys.forEach((k) => {
          obj[k] = Number(row[k]) || 0;
        });
        return obj;
      });
      return {
        chartType: effectiveChartType,
        xKey: "subject",
        yKeys: validYKeys,
        title,
        description,
        data,
      };
    }

    // ── Standard: bar / line / area / pie / donut / horizontal-bar / composed ─
    const data = rows.map((row) => {
      const obj: Record<string, any> = { [validXKey]: row[validXKey] };
      validYKeys.forEach((k) => {
        obj[k] = Number(row[k]) || 0;
      });
      return obj;
    });

    return {
      chartType: effectiveChartType,
      xKey: validXKey,
      yKeys: validYKeys,
      title,
      description,
      data,
    };
  }, [recommendation, rows, columns, userChartType]);

  const setChartType = (type: ChartType) => {
    setUserChartType(type === recommendedType ? null : type);
  };

  return {
    chartConfig,
    activeChartType,
    setChartType,
    hasVisualization: activeChartType !== "none" && chartConfig !== null,
    recommendedType,
  };
}
