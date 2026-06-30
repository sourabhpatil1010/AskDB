import {
  ComposedChart,
  Bar,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import { getChartColor, formatNumber, truncateLabel } from "@/utils/chart-utils";

interface ComposedChartViewProps {
  data: Record<string, any>[];
  xKey: string;
  yKeys: string[];
}

const CustomTooltip = ({ active, payload, label }: any) => {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-card border border-border rounded-xl p-3 shadow-xl text-xs">
      <p className="font-semibold text-foreground mb-2">{String(label)}</p>
      {payload.map((entry: any, i: number) => (
        <div key={i} className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full" style={{ background: entry.fill || entry.stroke }} />
          <span className="text-muted-foreground">{entry.name}:</span>
          <span className="font-medium text-foreground">{formatNumber(entry.value)}</span>
        </div>
      ))}
    </div>
  );
};

export function ComposedChartView({ data, xKey, yKeys }: ComposedChartViewProps) {
  // First metric as bar, remaining as lines
  const [barKey, ...lineKeys] = yKeys;

  return (
    <ResponsiveContainer width="100%" height={320}>
      <ComposedChart data={data} margin={{ top: 8, right: 24, left: 0, bottom: 40 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" vertical={false} />
        <XAxis
          dataKey={xKey}
          tickFormatter={(v) => truncateLabel(String(v))}
          tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }}
          axisLine={false}
          tickLine={false}
          angle={data.length > 8 ? -35 : 0}
          textAnchor={data.length > 8 ? "end" : "middle"}
        />
        <YAxis
          tickFormatter={formatNumber}
          tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }}
          axisLine={false}
          tickLine={false}
          width={50}
        />
        <Tooltip content={<CustomTooltip />} cursor={{ fill: "hsl(var(--muted))" }} />
        <Legend wrapperStyle={{ fontSize: 12 }} />
        {barKey && (
          <Bar
            dataKey={barKey}
            fill={getChartColor(0)}
            radius={[4, 4, 0, 0]}
            isAnimationActive
            animationDuration={700}
          />
        )}
        {lineKeys.map((key, i) => (
          <Line
            key={key}
            type="monotone"
            dataKey={key}
            stroke={getChartColor(i + 1)}
            strokeWidth={2.5}
            dot={{ r: 4, fill: getChartColor(i + 1), strokeWidth: 2, stroke: "hsl(var(--card))" }}
            isAnimationActive
            animationDuration={800}
          />
        ))}
      </ComposedChart>
    </ResponsiveContainer>
  );
}
