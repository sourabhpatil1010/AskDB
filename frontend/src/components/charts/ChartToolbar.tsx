import {
  BarChart2,
  AlignLeft,
  TrendingUp,
  PieChart,
  Hexagon,
  LayoutTemplate,
  Download,
  Maximize2,
  Minimize2,
  Sparkles,
} from "lucide-react";
import type { ChartType } from "@/types/chart";
import { exportSVG, exportPNG, exportCSV, exportExcel } from "@/utils/chart-utils";
import { toast } from "sonner";

interface ChartToolbarProps {
  activeType: ChartType;
  recommendedType: ChartType;
  onTypeChange: (type: ChartType) => void;
  containerId: string;
  data: Record<string, any>[];
  isFullscreen: boolean;
  onToggleFullscreen: () => void;
  title?: string;
}

const CHART_BUTTONS: { type: ChartType; label: string; Icon: React.FC<any> }[] = [
  { type: "bar", label: "Bar", Icon: BarChart2 },
  { type: "horizontal-bar", label: "H-Bar", Icon: AlignLeft },
  { type: "line", label: "Line", Icon: TrendingUp },
  { type: "area", label: "Area", Icon: () => (
    <svg viewBox="0 0 16 16" className="w-3.5 h-3.5" fill="currentColor">
      <path d="M0 14l4-6 4 3 4-8 4 5v6H0z" opacity=".5"/>
      <path d="M0 14l4-6 4 3 4-8 4 5" fill="none" stroke="currentColor" strokeWidth="1.5"/>
    </svg>
  )},
  { type: "pie", label: "Pie", Icon: PieChart },
  { type: "donut", label: "Donut", Icon: () => (
    <svg viewBox="0 0 16 16" className="w-3.5 h-3.5" fill="none" stroke="currentColor" strokeWidth="1.5">
      <circle cx="8" cy="8" r="6"/>
      <circle cx="8" cy="8" r="3"/>
    </svg>
  )},
  { type: "scatter", label: "Scatter", Icon: () => (
    <svg viewBox="0 0 16 16" className="w-3.5 h-3.5" fill="currentColor">
      <circle cx="3" cy="12" r="1.5"/><circle cx="7" cy="7" r="1.5"/>
      <circle cx="11" cy="4" r="1.5"/><circle cx="13" cy="10" r="1.5"/>
      <circle cx="5" cy="5" r="1.5"/>
    </svg>
  )},
  { type: "radar", label: "Radar", Icon: Hexagon },
  { type: "composed", label: "Composed", Icon: LayoutTemplate },
];

export function ChartToolbar({
  activeType,
  recommendedType,
  onTypeChange,
  containerId,
  data,
  isFullscreen,
  onToggleFullscreen,
  title = "chart",
}: ChartToolbarProps) {
  const safeFileName = title.replace(/[^a-z0-9]/gi, "_").toLowerCase();

  const handleExport = async (format: "png" | "svg" | "csv" | "excel") => {
    try {
      if (format === "png") exportPNG(containerId, `${safeFileName}.png`);
      else if (format === "svg") exportSVG(containerId, `${safeFileName}.svg`);
      else if (format === "csv") exportCSV(data, `${safeFileName}.csv`);
      else await exportExcel(data, `${safeFileName}.xlsx`);
      toast.success(`Exported as ${format.toUpperCase()}`);
    } catch {
      toast.error(`Export failed`);
    }
  };

  return (
    <div className="flex flex-wrap items-center justify-between gap-3 px-4 py-3 border-b border-border">
      {/* Chart Type Switcher */}
      <div className="flex items-center gap-1 flex-wrap">
        <span className="text-xs text-muted-foreground mr-1 hidden sm:inline">Chart:</span>
        {CHART_BUTTONS.map(({ type, label, Icon }) => (
          <button
            key={type}
            onClick={() => onTypeChange(type)}
            title={label}
            className={`flex items-center gap-1.5 px-2.5 py-1.5 text-xs rounded-lg border transition-all ${
              activeType === type
                ? "bg-primary text-primary-foreground border-primary shadow-sm shadow-primary/30"
                : "border-border text-muted-foreground hover:text-foreground hover:border-primary/30 hover:bg-muted/30"
            }`}
          >
            <Icon className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">{label}</span>
            {type === recommendedType && (
              <Sparkles className="w-2.5 h-2.5 text-amber-400" title="AI recommended" />
            )}
          </button>
        ))}
      </div>

      {/* Export + Fullscreen */}
      <div className="flex items-center gap-1.5">
        <div className="flex items-center gap-1 bg-muted/30 rounded-lg border border-border px-1 py-1">
          <Download className="w-3 h-3 text-muted-foreground ml-1" />
          {(["png", "svg", "csv", "excel"] as const).map((fmt) => (
            <button
              key={fmt}
              onClick={() => handleExport(fmt)}
              className="px-2 py-0.5 text-xs text-muted-foreground hover:text-foreground hover:bg-muted rounded transition-colors"
            >
              {fmt.toUpperCase()}
            </button>
          ))}
        </div>
        <button
          onClick={onToggleFullscreen}
          className="p-1.5 rounded-lg border border-border text-muted-foreground hover:text-foreground hover:bg-muted/30 transition-colors"
          title={isFullscreen ? "Exit fullscreen" : "Fullscreen"}
        >
          {isFullscreen ? (
            <Minimize2 className="w-3.5 h-3.5" />
          ) : (
            <Maximize2 className="w-3.5 h-3.5" />
          )}
        </button>
      </div>
    </div>
  );
}
