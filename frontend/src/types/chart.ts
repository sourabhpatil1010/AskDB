// ─── Chart Type Enum ────────────────────────────────────────────────────────

export type ChartType =
  | "bar"
  | "horizontal-bar"
  | "line"
  | "area"
  | "pie"
  | "donut"
  | "scatter"
  | "radar"
  | "composed"
  | "none";

// ─── Column Classification ───────────────────────────────────────────────────

export type ColumnKind = "date" | "numeric" | "category" | "text" | "unknown";

export interface ColumnMeta {
  name: string;
  kind: ColumnKind;
  /** sample of non-null values (up to 20) */
  sample: any[];
  /** true if all non-null sample values are unique */
  isHighCardinality: boolean;
  /** count of distinct values in sample */
  distinctCount: number;
}

// ─── Chart Recommendation ────────────────────────────────────────────────────

export interface ChartRecommendation {
  chartType: ChartType;
  /** column name to use as X axis (category/date) */
  xKey: string;
  /** column name(s) to plot as Y axis (numeric) */
  yKeys: string[];
  /** human-readable title */
  title: string;
  /** short description of why this chart was recommended */
  description: string;
  /** confidence score 0-1 */
  confidence: number;
}

// ─── Chart Config (user-facing, mutable) ────────────────────────────────────

export interface ChartConfig {
  chartType: ChartType;
  xKey: string;
  yKeys: string[];
  title: string;
  description: string;
  /** data already transformed for recharts (array of objects) */
  data: Record<string, any>[];
}

// ─── Available Chart Type Option (for toolbar switcher) ─────────────────────

export interface ChartTypeOption {
  type: ChartType;
  label: string;
  icon: string;
}

export const CHART_TYPE_OPTIONS: ChartTypeOption[] = [
  { type: "bar", label: "Bar", icon: "BarChart2" },
  { type: "horizontal-bar", label: "H-Bar", icon: "AlignLeft" },
  { type: "line", label: "Line", icon: "TrendingUp" },
  { type: "area", label: "Area", icon: "AreaChart" },
  { type: "pie", label: "Pie", icon: "PieChart" },
  { type: "donut", label: "Donut", icon: "Donut" },
  { type: "scatter", label: "Scatter", icon: "ScatterChart" },
  { type: "radar", label: "Radar", icon: "Hexagon" },
  { type: "composed", label: "Composed", icon: "LayoutTemplate" },
];
