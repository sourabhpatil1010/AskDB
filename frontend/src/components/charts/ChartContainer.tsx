import { useState, useId } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Sparkles, BarChart3 } from "lucide-react";
import type { ChartConfig, ChartType } from "@/types/chart";
import { ChartToolbar } from "./ChartToolbar";
import { BarChartView } from "./BarChartView";
import { LineChartView } from "./LineChartView";
import { AreaChartView } from "./AreaChartView";
import { PieChartView } from "./PieChartView";
import { ScatterChartView } from "./ScatterChartView";
import { RadarChartView } from "./RadarChartView";
import { ComposedChartView } from "./ComposedChartView";
import { EmptyChartState } from "./EmptyChartState";

interface ChartContainerProps {
  chartConfig: ChartConfig | null;
  activeChartType: ChartType;
  recommendedType: ChartType;
  onTypeChange: (type: ChartType) => void;
}

function ChartRenderer({ config }: { config: ChartConfig }) {
  const { chartType, data, xKey, yKeys } = config;

  if (!data.length) return <EmptyChartState message="No data points to render." />;

  switch (chartType) {
    case "bar":
      return <BarChartView data={data} xKey={xKey} yKeys={yKeys} />;
    case "horizontal-bar":
      return <BarChartView data={data} xKey={xKey} yKeys={yKeys} horizontal />;
    case "line":
      return <LineChartView data={data} xKey={xKey} yKeys={yKeys} />;
    case "area":
      return <AreaChartView data={data} xKey={xKey} yKeys={yKeys} />;
    case "pie":
      return <PieChartView data={data} xKey={xKey} yKeys={yKeys} />;
    case "donut":
      return <PieChartView data={data} xKey={xKey} yKeys={yKeys} donut />;
    case "scatter":
      return <ScatterChartView data={data} xKey={xKey} yKeys={yKeys} />;
    case "radar":
      return <RadarChartView data={data} xKey={xKey} yKeys={yKeys} />;
    case "composed":
      return <ComposedChartView data={data} xKey={xKey} yKeys={yKeys} />;
    default:
      return <EmptyChartState />;
  }
}

export function ChartContainer({
  chartConfig,
  activeChartType,
  recommendedType,
  onTypeChange,
}: ChartContainerProps) {
  const [isFullscreen, setIsFullscreen] = useState(false);
  const uid = useId().replace(/:/g, "");
  const containerId = `chart-container-${uid}`;

  const effectiveConfig = chartConfig
    ? { ...chartConfig, chartType: activeChartType }
    : null;

  const content = (
    <div
      className={`bg-card border border-border rounded-2xl overflow-hidden transition-all duration-300 ${
        isFullscreen
          ? "fixed inset-4 z-50 shadow-2xl rounded-2xl flex flex-col"
          : ""
      }`}
    >
      {/* Header */}
      <div className="px-5 py-4 border-b border-border flex items-center justify-between gap-3">
        <div className="flex items-center gap-3 min-w-0">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-violet-500 to-indigo-600 flex items-center justify-center shrink-0">
            <BarChart3 className="w-4 h-4 text-white" />
          </div>
          <div className="min-w-0">
            <h3 className="font-semibold text-sm text-foreground truncate">
              {effectiveConfig?.title || "Visualization"}
            </h3>
            {effectiveConfig?.description && (
              <p className="text-xs text-muted-foreground truncate">
                {effectiveConfig.description}
              </p>
            )}
          </div>
        </div>
        {recommendedType !== "none" && (
          <div className="flex items-center gap-1.5 shrink-0 px-2 py-1 bg-amber-500/10 border border-amber-500/20 rounded-lg">
            <Sparkles className="w-3 h-3 text-amber-500" />
            <span className="text-xs text-amber-600 dark:text-amber-400 font-medium">
              AI Recommended
            </span>
          </div>
        )}
      </div>

      {/* Toolbar */}
      <ChartToolbar
        activeType={activeChartType}
        recommendedType={recommendedType}
        onTypeChange={onTypeChange}
        containerId={containerId}
        data={effectiveConfig?.data ?? []}
        isFullscreen={isFullscreen}
        onToggleFullscreen={() => setIsFullscreen((f) => !f)}
        title={effectiveConfig?.title}
      />

      {/* Chart Area */}
      <div
        id={containerId}
        className={`p-4 ${isFullscreen ? "flex-1 overflow-auto" : ""}`}
      >
        <AnimatePresence mode="wait">
          <motion.div
            key={activeChartType}
            initial={{ opacity: 0, scale: 0.98 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.97 }}
            transition={{ duration: 0.25, ease: "easeOut" }}
          >
            {effectiveConfig ? (
              <ChartRenderer config={effectiveConfig} />
            ) : (
              <EmptyChartState />
            )}
          </motion.div>
        </AnimatePresence>
      </div>

      {/* Footer meta */}
      {effectiveConfig && (
        <div className="px-5 py-2.5 border-t border-border flex items-center justify-between text-xs text-muted-foreground bg-muted/10">
          <span>
            {effectiveConfig.data.length} data point
            {effectiveConfig.data.length !== 1 ? "s" : ""}
          </span>
          <span className="flex items-center gap-1">
            X: <code className="font-mono text-foreground/70">{effectiveConfig.xKey}</code>
            {" · "}
            Y: <code className="font-mono text-foreground/70">{effectiveConfig.yKeys.join(", ")}</code>
          </span>
        </div>
      )}
    </div>
  );

  return (
    <>
      {isFullscreen && (
        <div
          className="fixed inset-0 bg-background/80 backdrop-blur-sm z-40"
          onClick={() => setIsFullscreen(false)}
        />
      )}
      {content}
    </>
  );
}
