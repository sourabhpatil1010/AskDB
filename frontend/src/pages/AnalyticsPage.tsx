import { useMemo } from "react";
import { motion } from "framer-motion";
import { useQuery } from "@tanstack/react-query";
import {
  BarChart3,
  TrendingUp,
  Clock,
  CheckCircle2,
  XCircle,
  Activity,
} from "lucide-react";
import {
  AreaChart,
  Area,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";
import { historyApi } from "@/services/history.service";
import { formatMs } from "@/lib/utils";
import { formatCompactNumber, formatInteger, formatPercentageRaw } from "@/utils/formatters";
import { AnalyticsService } from "@/services/analytics.service";

const COLORS = [
  "hsl(262, 83%, 58%)",
  "hsl(217, 91%, 60%)",
  "hsl(162, 73%, 46%)",
  "hsl(25, 95%, 53%)",
  "hsl(340, 82%, 52%)",
  "hsl(47, 96%, 53%)",
  "hsl(292, 84%, 61%)",
  "hsl(199, 89%, 48%)",
];

export default function AnalyticsPage() {
  const { data: historyData, isLoading } = useQuery({
    queryKey: ["history"],
    queryFn: async () => {
      const result = await historyApi.getAll();
      return result.data;
    },
  });

  const history = historyData || [];

  const queryStats = useMemo(() => AnalyticsService.calculateStatistics(history), [history]);
  const stats = useMemo(() => ({
    total: queryStats.totalQueries,
    avgTime: queryStats.averageExecutionTime,
    successCount: queryStats.successfulQueries,
    errorCount: queryStats.failedQueries,
    successRate: queryStats.successRate,
  }), [queryStats]);

  // Queries per day chart data
  const queriesPerDay = useMemo(() => {
    const dayMap = new Map<string, number>();
    const last7Days: string[] = [];
    for (let i = 6; i >= 0; i--) {
      const d = new Date();
      d.setDate(d.getDate() - i);
      const key = d.toLocaleDateString("en-US", {
        month: "short",
        day: "numeric",
      });
      last7Days.push(key);
      dayMap.set(key, 0);
    }
    history.forEach((h) => {
      const d = new Date(h.created_at);
      const key = d.toLocaleDateString("en-US", {
        month: "short",
        day: "numeric",
      });
      if (dayMap.has(key)) {
        dayMap.set(key, (dayMap.get(key) || 0) + 1);
      }
    });
    return last7Days.map((day) => ({ name: day, queries: dayMap.get(day) || 0 }));
  }, [history]);

  // Average execution time per day
  const execTimePerDay = useMemo(() => {
    const dayMap = new Map<string, { sum: number; count: number }>();
    const last7Days: string[] = [];
    for (let i = 6; i >= 0; i--) {
      const d = new Date();
      d.setDate(d.getDate() - i);
      const key = d.toLocaleDateString("en-US", {
        month: "short",
        day: "numeric",
      });
      last7Days.push(key);
      dayMap.set(key, { sum: 0, count: 0 });
    }
    history.forEach((h) => {
      const d = new Date(h.created_at);
      const key = d.toLocaleDateString("en-US", {
        month: "short",
        day: "numeric",
      });
      if (dayMap.has(key)) {
        const entry = dayMap.get(key)!;
        entry.sum += h.execution_time_ms || 0;
        entry.count += 1;
      }
    });
    return last7Days.map((day) => {
      const entry = dayMap.get(day)!;
      return {
        name: day,
        avgTime: entry.count > 0 ? Math.round(entry.sum / entry.count) : 0,
      };
    });
  }, [history]);

  // Most queried terms (approximate from natural language)
  const topQueries = useMemo(() => {
    const wordMap = new Map<string, number>();
    const keywords = [
      "employees",
      "departments",
      "salary",
      "projects",
      "payroll",
      "attendance",
      "offices",
      "skills",
    ];
    history.forEach((h) => {
      const text = h.natural_language.toLowerCase();
      keywords.forEach((kw) => {
        if (text.includes(kw)) {
          wordMap.set(kw, (wordMap.get(kw) || 0) + 1);
        }
      });
    });
    return Array.from(wordMap.entries())
      .map(([name, value]) => ({ name, value }))
      .sort((a, b) => b.value - a.value)
      .slice(0, 6);
  }, [history]);

  const statCards = [
    {
      label: "Total Queries",
      value: stats.total.toString(),
      icon: BarChart3,
      gradient: "from-violet-500 to-purple-600",
    },
    {
      label: "Avg. Execution Time",
      value: formatMs(stats.avgTime),
      icon: Clock,
      gradient: "from-blue-500 to-cyan-500",
    },
    {
      label: "Success Rate",
      value: formatPercentageRaw(stats.successRate, 1),
      icon: CheckCircle2,
      gradient: "from-emerald-500 to-green-500",
    },
    {
      label: "Error Count",
      value: stats.errorCount.toString(),
      icon: XCircle,
      gradient: "from-red-500 to-rose-500",
    },
  ];

  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      return (
        <div className="bg-card border border-border rounded-xl p-3 shadow-xl">
          <p className="text-xs font-medium text-foreground mb-1">{label}</p>
          {payload.map((p: any, i: number) => (
            <p key={i} className="text-xs text-muted-foreground">
              {p.name}:{" "}
              <span className="text-foreground font-medium">
                {formatCompactNumber(p.value)}
              </span>
            </p>
          ))}
        </div>
      );
    }
    return null;
  };

  return (
    <div className="p-6 lg:p-8 max-w-[1400px] mx-auto">
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
      >
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-2xl font-bold text-foreground flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-violet-500 to-purple-600 flex items-center justify-center shadow-lg">
              <BarChart3 className="w-5 h-5 text-white" />
            </div>
            Analytics
          </h1>
          <p className="text-muted-foreground mt-2 text-sm">
            Insights and metrics from your database queries.
          </p>
        </div>

        {/* Stat Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          {statCards.map((stat) => {
            const Icon = stat.icon;
            return (
              <motion.div
                key={stat.label}
                whileHover={{ y: -2 }}
                className="bg-card border border-border rounded-2xl p-5"
              >
                <div className="flex items-center justify-between mb-3">
                  <div
                    className={`w-10 h-10 rounded-xl bg-gradient-to-br ${stat.gradient} flex items-center justify-center shadow-lg`}
                  >
                    <Icon className="w-5 h-5 text-white" />
                  </div>
                </div>
                <div className="text-2xl font-bold text-foreground mb-1">
                  {isLoading ? (
                    <div className="h-7 w-16 skeleton-shimmer rounded" />
                  ) : (
                    stat.value
                  )}
                </div>
                <div className="text-sm text-muted-foreground">{stat.label}</div>
              </motion.div>
            );
          })}
        </div>

        {/* Charts Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Queries Over Time */}
          <div className="bg-card border border-border rounded-2xl p-6">
            <div className="flex items-center gap-2 mb-6">
              <Activity className="w-4 h-4 text-primary" />
              <h3 className="font-semibold text-foreground">Queries Over Time</h3>
              <span className="text-xs text-muted-foreground ml-auto">Last 7 days</span>
            </div>
            <div className="h-[280px]">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={queriesPerDay}>
                  <defs>
                    <linearGradient id="colorQueries" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="hsl(262, 83%, 58%)" stopOpacity={0.3} />
                      <stop offset="95%" stopColor="hsl(262, 83%, 58%)" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                  <XAxis
                    dataKey="name"
                    tick={{ fill: "hsl(var(--muted-foreground))", fontSize: 11 }}
                    axisLine={{ stroke: "hsl(var(--border))" }}
                  />
                  <YAxis
                    tick={{ fill: "hsl(var(--muted-foreground))", fontSize: 11 }}
                    axisLine={{ stroke: "hsl(var(--border))" }}
                    allowDecimals={false}
                  />
                  <Tooltip content={<CustomTooltip />} />
                  <Area
                    type="monotone"
                    dataKey="queries"
                    stroke="hsl(262, 83%, 58%)"
                    fillOpacity={1}
                    fill="url(#colorQueries)"
                    strokeWidth={2}
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Avg Execution Time */}
          <div className="bg-card border border-border rounded-2xl p-6">
            <div className="flex items-center gap-2 mb-6">
              <Clock className="w-4 h-4 text-blue-500" />
              <h3 className="font-semibold text-foreground">Avg. Execution Time</h3>
              <span className="text-xs text-muted-foreground ml-auto">Last 7 days</span>
            </div>
            <div className="h-[280px]">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={execTimePerDay}>
                  <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                  <XAxis
                    dataKey="name"
                    tick={{ fill: "hsl(var(--muted-foreground))", fontSize: 11 }}
                    axisLine={{ stroke: "hsl(var(--border))" }}
                  />
                  <YAxis
                    tick={{ fill: "hsl(var(--muted-foreground))", fontSize: 11 }}
                    axisLine={{ stroke: "hsl(var(--border))" }}
                    unit="ms"
                  />
                  <Tooltip content={<CustomTooltip />} />
                  <Bar
                    dataKey="avgTime"
                    name="Avg Time (ms)"
                    fill="hsl(217, 91%, 60%)"
                    radius={[6, 6, 0, 0]}
                  />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Most Queried Topics */}
          <div className="bg-card border border-border rounded-2xl p-6">
            <div className="flex items-center gap-2 mb-6">
              <TrendingUp className="w-4 h-4 text-emerald-500" />
              <h3 className="font-semibold text-foreground">Most Queried Topics</h3>
            </div>
            {topQueries.length > 0 ? (
              <div className="h-[280px]">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={topQueries}
                      cx="50%"
                      cy="50%"
                      innerRadius={70}
                      outerRadius={110}
                      paddingAngle={4}
                      dataKey="value"
                    >
                      {topQueries.map((_, index) => (
                        <Cell
                          key={`cell-${index}`}
                          fill={COLORS[index % COLORS.length]}
                        />
                      ))}
                    </Pie>
                    <Tooltip content={<CustomTooltip />} />
                    <Legend
                      wrapperStyle={{ fontSize: "12px" }}
                      formatter={(value) => (
                        <span style={{ color: "hsl(var(--foreground))" }}>{value}</span>
                      )}
                    />
                  </PieChart>
                </ResponsiveContainer>
              </div>
            ) : (
              <div className="h-[280px] flex items-center justify-center text-muted-foreground text-sm">
                No query data available yet
              </div>
            )}
          </div>

          {/* Query Performance Distribution */}
          <div className="bg-card border border-border rounded-2xl p-6">
            <div className="flex items-center gap-2 mb-6">
              <BarChart3 className="w-4 h-4 text-amber-500" />
              <h3 className="font-semibold text-foreground">Performance Summary</h3>
            </div>
            <div className="space-y-6">
              <div>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm text-muted-foreground">Fast (&lt;100ms)</span>
                  <span className="text-sm font-medium text-foreground">
                    {history.filter((h) => (h.execution_time_ms || 0) < 100).length}
                  </span>
                </div>
                <div className="w-full h-2 bg-muted/30 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-emerald-500 rounded-full transition-all duration-500"
                    style={{
                      width: `${
                        history.length > 0
                          ? (history.filter((h) => (h.execution_time_ms || 0) < 100)
                              .length /
                              history.length) *
                            100
                          : 0
                      }%`,
                    }}
                  />
                </div>
              </div>
              <div>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm text-muted-foreground">
                    Medium (100-500ms)
                  </span>
                  <span className="text-sm font-medium text-foreground">
                    {
                      history.filter(
                        (h) =>
                          (h.execution_time_ms || 0) >= 100 &&
                          (h.execution_time_ms || 0) < 500
                      ).length
                    }
                  </span>
                </div>
                <div className="w-full h-2 bg-muted/30 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-amber-500 rounded-full transition-all duration-500"
                    style={{
                      width: `${
                        history.length > 0
                          ? (history.filter(
                              (h) =>
                                (h.execution_time_ms || 0) >= 100 &&
                                (h.execution_time_ms || 0) < 500
                            ).length /
                              history.length) *
                            100
                          : 0
                      }%`,
                    }}
                  />
                </div>
              </div>
              <div>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm text-muted-foreground">
                    Slow (&gt;500ms)
                  </span>
                  <span className="text-sm font-medium text-foreground">
                    {
                      history.filter((h) => (h.execution_time_ms || 0) >= 500)
                        .length
                    }
                  </span>
                </div>
                <div className="w-full h-2 bg-muted/30 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-red-500 rounded-full transition-all duration-500"
                    style={{
                      width: `${
                        history.length > 0
                          ? (history.filter(
                              (h) => (h.execution_time_ms || 0) >= 500
                            ).length /
                              history.length) *
                            100
                          : 0
                      }%`,
                    }}
                  />
                </div>
              </div>
              <div className="pt-4 border-t border-border">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-muted-foreground">
                    Overall Success Rate
                  </span>
                  <span className="text-lg font-bold text-emerald-500">
                    {formatPercentageRaw(stats.successRate, 1)}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </motion.div>
    </div>
  );
}
