import { useMemo, useState } from "react";
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
 */
export function useChartData({ columns, rows }: UseChartDataInput): UseChartDataResult {
  // Run recommendation engine — memoized on columns/rows changes only
  const recommendation = useMemo(() => {
    if (!columns.length || !rows.length) return null;
    return ChartRecommendationEngine.recommend(columns, rows);
  }, [columns, rows]);

  const recommendedType: ChartType = recommendation?.chartType ?? "none";

  // User can override the recommended chart type
  const [userChartType, setUserChartType] = useState<ChartType | null>(null);

  // Reset user override when dataset changes
  const activeChartType: ChartType = userChartType ?? recommendedType;

  // Build chart-ready data object — memoized
  const chartConfig = useMemo((): ChartConfig | null => {
    if (!recommendation || recommendation.chartType === "none") return null;

    const { xKey, yKeys, title, description } = recommendation;
    const effectiveChartType = userChartType ?? recommendation.chartType;

    // For scatter charts, we need {x, y} format
    if (effectiveChartType === "scatter" && yKeys.length >= 1) {
      const data = rows.map((row) => ({
        x: Number(row[xKey]) || 0,
        y: Number(row[yKeys[0]]) || 0,
        ...Object.fromEntries(
          Object.entries(row).filter(([k]) => k !== xKey && k !== yKeys[0]),
        ),
      }));
      return { chartType: effectiveChartType, xKey: "x", yKeys: ["y"], title, description, data };
    }

    // For radar charts — reshape to { subject, [metric]: value }
    if (effectiveChartType === "radar") {
      if (!xKey || yKeys.length === 0) return null;
      // If xKey is a label column, use rows as-is (each row is a data point)
      const data = rows.map((row) => {
        const obj: Record<string, any> = { subject: String(row[xKey] ?? row[columns[0]]) };
        yKeys.forEach((k) => { obj[k] = Number(row[k]) || 0; });
        return obj;
      });
      return { chartType: effectiveChartType, xKey: "subject", yKeys, title, description, data };
    }

    // Standard format for bar/line/area/pie/horizontal-bar/composed
    const data = rows.map((row) => {
      const obj: Record<string, any> = { [xKey]: row[xKey] };
      yKeys.forEach((k) => { obj[k] = Number(row[k]) || 0; });
      return obj;
    });

    return { chartType: effectiveChartType, xKey, yKeys, title, description, data };
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
