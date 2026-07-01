import { PieChart, Pie, Cell, Tooltip, Legend, ResponsiveContainer } from "recharts";
import {
  getChartColor,
  formatDecimal,
  formatPercentage,
  formatColumnLabel,
  truncateLabel,
} from "@/utils/chart-utils";

interface PieChartViewProps {
  data: Record<string, any>[];
  xKey: string;
  yKeys: string[];
  donut?: boolean;
}

const RADIAN = Math.PI / 180;

const renderCustomLabel = ({
  cx, cy, midAngle, innerRadius, outerRadius, percent, value, index,
}: any) => {
  if (
    value === null ||
    value === undefined ||
    Number(value) === 0 ||
    isNaN(Number(value)) ||
    percent <= 0
  ) {
    return null;
  }
  const formattedPct = formatPercentage(percent);

  // To display percentage labels on EVERY visible slice without hiding smaller slices,
  // we remove minPercentRequired and instead use radial staggering. For smaller slices (< 5%),
  // we alternate the radial offset (0.75 vs 0.55) and use a slightly smaller font size so
  // adjacent labels do not collide.
  const isSmallSlice = percent < 0.05;
  const staggerOffset = isSmallSlice ? (index % 2 === 0 ? 0.75 : 0.55) : 0.65;
  const radius = innerRadius + (outerRadius - innerRadius) * staggerOffset;
  const x = cx + radius * Math.cos(-midAngle * RADIAN);
  const y = cy + radius * Math.sin(-midAngle * RADIAN);

  return (
    <text
      x={x}
      y={y}
      fill="white"
      textAnchor="middle"
      dominantBaseline="central"
      fontSize={isSmallSlice ? 10 : 11}
      fontWeight={600}
      className="select-none drop-shadow-md"
      style={{ pointerEvents: "none", textShadow: "0 1px 2px rgba(0,0,0,0.6)" }}
    >
      {formattedPct}
    </text>
  );
};

const CustomTooltip = ({ active, payload, xKey, valueKey }: any) => {
  if (!active || !payload?.length) return null;
  const entry = payload[0];
  const xLabel = formatColumnLabel(xKey || "Category");
  const yLabel = formatColumnLabel(valueKey || "Value");
  const percentVal = entry.payload?.percent ?? 0;
  const formattedVal = formatDecimal(entry.value);
  const formattedPct = formatPercentage(percentVal);

  return (
    <div className="bg-card border border-border rounded-xl p-3 shadow-xl text-xs space-y-1.5 min-w-[180px]">
      <div className="flex items-center gap-2 font-semibold text-foreground pb-1.5 border-b border-border/50">
        <span
          className="w-2.5 h-2.5 rounded-full shrink-0"
          style={{ background: entry.payload?.fill || entry.color || "#7c3aed" }}
        />
        <span>
          {xLabel}: <span className="font-bold">{String(entry.name)}</span>
        </span>
      </div>
      <div className="text-muted-foreground flex items-center justify-between gap-4">
        <span>{yLabel}:</span>
        <span className="text-foreground font-semibold font-mono">{formattedVal}</span>
      </div>
      <div className="text-muted-foreground flex items-center justify-between gap-4">
        <span>Percentage:</span>
        <span className="text-foreground font-semibold font-mono">{formattedPct}</span>
      </div>
    </div>
  );
};

export function PieChartView({ data, xKey, yKeys, donut = false }: PieChartViewProps) {
  const valueKey = yKeys[0];
  const total = data.reduce((sum, row) => sum + (Number(row[valueKey]) || 0), 0);

  const chartData = data.map((row) => ({
    name: String(row[xKey]),
    value: Number(row[valueKey]) || 0,
    percent: (Number(row[valueKey]) || 0) / (total || 1),
  }));

  const outerRadius = donut ? 120 : 130;
  const innerRadius = donut ? 65 : 0;

  return (
    <ResponsiveContainer width="100%" height={320}>
      <PieChart>
        {donut && (
          <text
            x="50%"
            y="50%"
            textAnchor="middle"
            dominantBaseline="middle"
            className="fill-foreground"
            style={{ fill: "hsl(var(--foreground))" }}
          >
            <tspan x="50%" dy="-8" fontSize={22} fontWeight={700}>
              {formatDecimal(total)}
            </tspan>
            <tspan x="50%" dy={20} fontSize={11} fill="hsl(var(--muted-foreground))">
              Total
            </tspan>
          </text>
        )}
        <Pie
          data={chartData}
          cx="50%"
          cy="50%"
          innerRadius={innerRadius}
          outerRadius={outerRadius}
          paddingAngle={donut ? 3 : 1}
          dataKey="value"
          labelLine={false}
          label={renderCustomLabel}
          isAnimationActive
          animationDuration={800}
          animationEasing="ease-out"
        >
          {chartData.map((_, index) => (
            <Cell key={index} fill={getChartColor(index)} stroke="hsl(var(--card))" strokeWidth={2} />
          ))}
        </Pie>
        <Tooltip content={<CustomTooltip xKey={xKey} valueKey={valueKey} />} />
        <Legend
          formatter={(value) => (
            <span style={{ fontSize: 12, color: "hsl(var(--foreground))" }}>
              {truncateLabel(String(value), 20)}
            </span>
          )}
          wrapperStyle={{ paddingTop: 8 }}
        />
      </PieChart>
    </ResponsiveContainer>
  );
}
