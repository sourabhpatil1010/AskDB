import {
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ZAxis,
} from "recharts";
import { formatNumber } from "@/utils/chart-utils";

interface ScatterChartViewProps {
  data: Record<string, any>[];
  xKey: string;
  yKeys: string[];
}

const CustomTooltip = ({ active, payload }: any) => {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-card border border-border rounded-xl p-3 shadow-xl text-xs">
      {payload.map((entry: any, i: number) => (
        <div key={i} className="flex items-center gap-2">
          <span className="text-muted-foreground">{entry.name}:</span>
          <span className="font-medium text-foreground">{formatNumber(entry.value)}</span>
        </div>
      ))}
    </div>
  );
};

export function ScatterChartView({ data, xKey, yKeys }: ScatterChartViewProps) {
  const yKey = yKeys[0] ?? "y";

  return (
    <ResponsiveContainer width="100%" height={320}>
      <ScatterChart margin={{ top: 8, right: 24, left: 0, bottom: 8 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
        <XAxis
          type="number"
          dataKey={xKey}
          name={xKey}
          tickFormatter={formatNumber}
          tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }}
          axisLine={false}
          tickLine={false}
          label={{
            value: xKey,
            position: "insideBottom",
            offset: -5,
            style: { fontSize: 11, fill: "hsl(var(--muted-foreground))" },
          }}
        />
        <YAxis
          type="number"
          dataKey={yKey}
          name={yKey}
          tickFormatter={formatNumber}
          tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }}
          axisLine={false}
          tickLine={false}
          width={55}
          label={{
            value: yKey,
            angle: -90,
            position: "insideLeft",
            style: { fontSize: 11, fill: "hsl(var(--muted-foreground))" },
          }}
        />
        <ZAxis range={[40, 40]} />
        <Tooltip content={<CustomTooltip />} cursor={{ strokeDasharray: "3 3" }} />
        <Scatter
          data={data}
          fill="#7c3aed"
          fillOpacity={0.75}
          isAnimationActive
          animationDuration={700}
          animationEasing="ease-out"
        />
      </ScatterChart>
    </ResponsiveContainer>
  );
}
