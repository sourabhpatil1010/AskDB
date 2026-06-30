import {
  RadarChart,
  Radar,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import { getChartColor, formatNumber, truncateLabel } from "@/utils/chart-utils";

interface RadarChartViewProps {
  data: Record<string, any>[];
  xKey: string;
  yKeys: string[];
}

const CustomTooltip = ({ active, payload }: any) => {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-card border border-border rounded-xl p-3 shadow-xl text-xs">
      <p className="font-semibold text-foreground mb-2">{payload[0]?.payload?.subject}</p>
      {payload.map((entry: any, i: number) => (
        <div key={i} className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full" style={{ background: entry.stroke }} />
          <span className="text-muted-foreground">{entry.name}:</span>
          <span className="font-medium text-foreground">{formatNumber(entry.value)}</span>
        </div>
      ))}
    </div>
  );
};

export function RadarChartView({ data, xKey, yKeys }: RadarChartViewProps) {
  const isMulti = yKeys.length > 1;
  // For radar, if we have few rows and many metrics, transpose: each row is a subject
  // If we have many rows and few metrics, each metric is a dimension
  const chartData = data.slice(0, 12); // cap at 12 spokes

  return (
    <ResponsiveContainer width="100%" height={360}>
      <RadarChart cx="50%" cy="50%" outerRadius={130} data={chartData}>
        <PolarGrid stroke="hsl(var(--border))" />
        <PolarAngleAxis
          dataKey={xKey}
          tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }}
          tickFormatter={(v) => truncateLabel(String(v), 12)}
        />
        <PolarRadiusAxis
          angle={30}
          tick={{ fontSize: 10, fill: "hsl(var(--muted-foreground))" }}
          tickFormatter={formatNumber}
          axisLine={false}
        />
        <Tooltip content={<CustomTooltip />} />
        {isMulti && <Legend wrapperStyle={{ fontSize: 12 }} />}
        {yKeys.map((key, i) => (
          <Radar
            key={key}
            name={key}
            dataKey={key}
            stroke={getChartColor(i)}
            fill={getChartColor(i)}
            fillOpacity={0.15}
            strokeWidth={2}
            isAnimationActive
            animationDuration={800}
            animationEasing="ease-out"
          />
        ))}
      </RadarChart>
    </ResponsiveContainer>
  );
}
