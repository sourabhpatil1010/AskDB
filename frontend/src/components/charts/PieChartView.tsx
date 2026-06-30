import { PieChart, Pie, Cell, Tooltip, Legend, ResponsiveContainer } from "recharts";
import { getChartColor, formatNumber, truncateLabel } from "@/utils/chart-utils";

interface PieChartViewProps {
  data: Record<string, any>[];
  xKey: string;
  yKeys: string[];
  donut?: boolean;
}

const RADIAN = Math.PI / 180;

const renderCustomLabel = ({
  cx, cy, midAngle, innerRadius, outerRadius, percent, name,
}: any) => {
  if (percent < 0.04) return null; // hide tiny slices
  const radius = innerRadius + (outerRadius - innerRadius) * 0.55;
  const x = cx + radius * Math.cos(-midAngle * RADIAN);
  const y = cy + radius * Math.sin(-midAngle * RADIAN);
  return (
    <text
      x={x}
      y={y}
      fill="white"
      textAnchor="middle"
      dominantBaseline="central"
      fontSize={11}
      fontWeight={600}
    >
      {`${(percent * 100).toFixed(0)}%`}
    </text>
  );
};

const CustomTooltip = ({ active, payload }: any) => {
  if (!active || !payload?.length) return null;
  const entry = payload[0];
  return (
    <div className="bg-card border border-border rounded-xl p-3 shadow-xl text-xs">
      <div className="flex items-center gap-2 mb-1">
        <span className="w-2 h-2 rounded-full" style={{ background: entry.payload.fill }} />
        <span className="font-semibold text-foreground">{String(entry.name)}</span>
      </div>
      <p className="text-muted-foreground">
        Value: <span className="text-foreground font-medium">{formatNumber(entry.value)}</span>
      </p>
      <p className="text-muted-foreground">
        Share: <span className="text-foreground font-medium">{(entry.payload.percent * 100).toFixed(1)}%</span>
      </p>
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
              {formatNumber(total)}
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
        <Tooltip content={<CustomTooltip />} />
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
