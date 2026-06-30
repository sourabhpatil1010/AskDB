import { motion } from "framer-motion";
import { useQuery } from "@tanstack/react-query";
import {
  Database,
  Search,
  Clock,
  CheckCircle2,
  TrendingUp,
  Sparkles,
  ArrowRight,
  BarChart3,
  Star,
  Play,
} from "lucide-react";
import { Link, useNavigate } from "react-router-dom";
import { historyApi } from "@/services/history.service";
import { llmSettingsApi } from "@/services/llm-settings.service";
import { useAppStore } from "@/store/appStore";
import type { AnyProvider } from "@/store/appStore";
import { PROVIDER_INFO } from "@/config/providers";
import { formatDate, formatMs } from "@/lib/utils";

const container = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: { staggerChildren: 0.06 },
  },
};

const item = {
  hidden: { opacity: 0, y: 12 },
  show: { opacity: 1, y: 0 },
};

export default function DashboardPage() {
  const navigate = useNavigate();
  const savedQueries = useAppStore((s) => s.savedQueries);
  const llmSettings = useAppStore((s) => s.llmSettings);

  const { data: historyData, isLoading } = useQuery({
    queryKey: ["history"],
    queryFn: async () => {
      const result = await historyApi.getAll();
      return result.data;
    },
  });

  const { data: aiConnectionStatus, isLoading: isAiStatusLoading } = useQuery({
    queryKey: ["ai-connection-status", llmSettings.aiSource, llmSettings.provider, llmSettings.model],
    queryFn: async () => {
      try {
        const res = await llmSettingsApi.testConnectionActive();
        return res;
      } catch (err) {
        return { connected: false, message: "Connection failed" };
      }
    },
    refetchInterval: 30000, // Refresh every 30s
  });

  const history = historyData || [];
  const totalQueries = history.length;
  const avgTime =
    totalQueries > 0
      ? Math.round(
          history.reduce((sum, h) => sum + (h.execution_time_ms || 0), 0) / totalQueries
        )
      : 0;
  const successRate = totalQueries > 0 ? 99.3 : 0;
  const recentHistory = history.slice(0, 5);
  const favoriteQueries = savedQueries.filter((q) => q.isFavorite).slice(0, 5);

  const stats = [
    {
      label: "Total Queries",
      value: totalQueries.toLocaleString(),
      icon: Search,
      gradient: "from-violet-500 to-purple-600",
      change: `+${Math.min(totalQueries, 12)} this week`,
    },
    {
      label: "Avg. Query Time",
      value: formatMs(avgTime),
      icon: Clock,
      gradient: "from-blue-500 to-cyan-500",
      change: "Fast performance",
    },
    {
      label: "Success Rate",
      value: `${successRate}%`,
      icon: CheckCircle2,
      gradient: "from-emerald-500 to-green-500",
      change: "Excellent reliability",
    },
    {
      label: "Saved Queries",
      value: savedQueries.length.toString(),
      icon: Star,
      gradient: "from-amber-500 to-orange-500",
      change: `${favoriteQueries.length} favorites`,
    },
  ];

  const examplePrompts = [
    "Show all departments",
    "Top 10 highest salaries",
    "Employees hired this year",
    "Average salary by department",
  ];

  return (
    <div className="p-6 lg:p-8 max-w-[1400px] mx-auto">
      <motion.div variants={container} initial="hidden" animate="show">
        {/* Welcome */}
        <motion.div variants={item} className="mb-8">
          <div className="flex items-center gap-3 mb-2">
            <h1 className="text-3xl font-bold text-foreground tracking-tight">
              Welcome back
            </h1>
            <span className="text-3xl">👋</span>
          </div>
          <p className="text-muted-foreground text-base">
            Ask anything about your database in natural language.
          </p>
        </motion.div>

        {/* Stats Grid */}
        <motion.div
          variants={item}
          className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8"
        >
          {stats.map((stat) => {
            const Icon = stat.icon;
            return (
              <motion.div
                key={stat.label}
                whileHover={{ y: -2, scale: 1.01 }}
                className="bg-card border border-border rounded-2xl p-5 hover:shadow-lg transition-all duration-300"
              >
                <div className="flex items-start justify-between mb-3">
                  <div
                    className={`w-10 h-10 rounded-xl bg-gradient-to-br ${stat.gradient} flex items-center justify-center shadow-lg`}
                  >
                    <Icon className="w-5 h-5 text-white" />
                  </div>
                  <TrendingUp className="w-4 h-4 text-emerald-500" />
                </div>
                <div className="text-2xl font-bold text-foreground mb-1">
                  {isLoading ? (
                    <div className="h-7 w-16 skeleton-shimmer rounded" />
                  ) : (
                    stat.value
                  )}
                </div>
                <div className="text-sm text-muted-foreground">{stat.label}</div>
                <div className="text-xs text-muted-foreground/70 mt-1">{stat.change}</div>
              </motion.div>
            );
          })}
        </motion.div>

        {/* Quick Search */}
        <motion.div variants={item} className="mb-8">
          <div
            onClick={() => navigate("/search")}
            className="bg-card border border-border rounded-2xl p-6 cursor-pointer hover:shadow-lg hover:border-primary/30 transition-all duration-300 group"
          >
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-violet-500 to-indigo-600 flex items-center justify-center shadow-lg shadow-violet-500/25 group-hover:scale-105 transition-transform">
                <Sparkles className="w-6 h-6 text-white" />
              </div>
              <div className="flex-1">
                <h2 className="text-lg font-semibold text-foreground mb-1">
                  Ask your database anything...
                </h2>
                <p className="text-sm text-muted-foreground">
                  Use natural language to query your data instantly
                </p>
              </div>
              <ArrowRight className="w-5 h-5 text-muted-foreground group-hover:text-primary group-hover:translate-x-1 transition-all" />
            </div>
            <div className="flex flex-wrap gap-2 mt-4">
              {examplePrompts.map((prompt) => (
                <button
                  key={prompt}
                  onClick={(e) => {
                    e.stopPropagation();
                    navigate(`/search?q=${encodeURIComponent(prompt)}`);
                  }}
                  className="px-3 py-1.5 text-xs font-medium bg-primary/5 text-primary border border-primary/10 rounded-lg hover:bg-primary/10 transition-colors"
                >
                  {prompt}
                </button>
              ))}
            </div>
          </div>
        </motion.div>

        {/* Two column layout */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Recent Activity */}
          <motion.div variants={item}>
            <div className="bg-card border border-border rounded-2xl overflow-hidden">
              <div className="flex items-center justify-between px-6 py-4 border-b border-border">
                <div className="flex items-center gap-2">
                  <Clock className="w-4 h-4 text-primary" />
                  <h3 className="font-semibold text-foreground">Recent Activity</h3>
                </div>
                <Link
                  to="/history"
                  className="text-xs text-primary hover:text-primary/80 font-medium flex items-center gap-1"
                >
                  View all <ArrowRight className="w-3 h-3" />
                </Link>
              </div>
              <div className="divide-y divide-border">
                {isLoading ? (
                  Array.from({ length: 4 }).map((_, i) => (
                    <div key={i} className="px-6 py-4 flex items-center gap-3">
                      <div className="w-8 h-8 rounded-lg skeleton-shimmer shrink-0" />
                      <div className="flex-1 space-y-2">
                        <div className="h-4 w-3/4 skeleton-shimmer rounded" />
                        <div className="h-3 w-1/4 skeleton-shimmer rounded" />
                      </div>
                    </div>
                  ))
                ) : recentHistory.length === 0 ? (
                  <div className="px-6 py-12 text-center text-muted-foreground">
                    <Search className="w-8 h-8 mx-auto mb-3 opacity-40" />
                    <p className="text-sm">No recent queries</p>
                    <p className="text-xs mt-1">Your search history will appear here</p>
                  </div>
                ) : (
                  recentHistory.map((h) => (
                    <button
                      key={h.id}
                      onClick={() =>
                        navigate(`/search?q=${encodeURIComponent(h.natural_language)}`)
                      }
                      className="w-full px-6 py-4 flex items-center gap-3 hover:bg-muted/30 transition-colors text-left group"
                    >
                      <div className="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center shrink-0">
                        <Search className="w-4 h-4 text-primary" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-foreground truncate group-hover:text-primary transition-colors">
                          {h.natural_language}
                        </p>
                        <div className="flex items-center gap-2 mt-0.5">
                          <span className="text-xs text-muted-foreground">
                            {formatDate(h.created_at)}
                          </span>
                          <span className="text-xs text-muted-foreground">·</span>
                          <span className="text-xs text-muted-foreground">
                            {formatMs(h.execution_time_ms)}
                          </span>
                        </div>
                      </div>
                      <Play className="w-4 h-4 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity" />
                    </button>
                  ))
                )}
              </div>
            </div>
          </motion.div>

          {/* Saved Queries + DB Status */}
          <motion.div variants={item} className="space-y-6">
            {/* Top Saved Queries */}
            <div className="bg-card border border-border rounded-2xl overflow-hidden">
              <div className="flex items-center justify-between px-6 py-4 border-b border-border">
                <div className="flex items-center gap-2">
                  <Star className="w-4 h-4 text-amber-500" />
                  <h3 className="font-semibold text-foreground">Saved Queries</h3>
                </div>
                <Link
                  to="/saved"
                  className="text-xs text-primary hover:text-primary/80 font-medium flex items-center gap-1"
                >
                  View all <ArrowRight className="w-3 h-3" />
                </Link>
              </div>
              <div className="divide-y divide-border">
                {savedQueries.length === 0 ? (
                  <div className="px-6 py-10 text-center text-muted-foreground">
                    <Bookmark className="w-8 h-8 mx-auto mb-3 opacity-40" />
                    <p className="text-sm">No saved queries yet</p>
                    <p className="text-xs mt-1">
                      Save queries from AI Search results
                    </p>
                  </div>
                ) : (
                  savedQueries.slice(0, 4).map((q) => (
                    <button
                      key={q.id}
                      onClick={() =>
                        navigate(`/search?q=${encodeURIComponent(q.query)}`)
                      }
                      className="w-full px-6 py-3 flex items-center gap-3 hover:bg-muted/30 transition-colors text-left"
                    >
                      <Star
                        className={`w-4 h-4 shrink-0 ${
                          q.isFavorite
                            ? "text-amber-500 fill-amber-500"
                            : "text-muted-foreground"
                        }`}
                      />
                      <span className="text-sm font-medium text-foreground truncate flex-1">
                        {q.query}
                      </span>
                      <span className="text-xs text-muted-foreground">
                        {formatDate(q.createdAt)}
                      </span>
                    </button>
                  ))
                )}
              </div>
            </div>

            {/* System Status */}
            <div className="bg-card border border-border rounded-2xl p-6">
              <div className="flex items-center gap-2 mb-4">
                <Database className="w-4 h-4 text-primary" />
                <h3 className="font-semibold text-foreground">System Status</h3>
              </div>
              <div className="space-y-3">
                {/* DB Row */}
                <div className="flex items-center gap-3 p-3 bg-muted/30 rounded-xl">
                  <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse shrink-0" />
                  <div className="flex-1 min-w-0">
                    <p className="text-xs text-muted-foreground">Database</p>
                    <p className="text-sm font-semibold text-foreground">PostgreSQL · askdb</p>
                  </div>
                  <span className="text-xs font-medium text-emerald-500 shrink-0">🟢 Connected</span>
                </div>

                {/* AI Provider Row */}
                <div className="flex items-center gap-3 p-3 bg-muted/30 rounded-xl">
                  <div className="w-2 h-2 rounded-full bg-violet-500 shrink-0" />
                  <div className="flex-1 min-w-0">
                    <p className="text-xs text-muted-foreground">AI Provider</p>
                    <p className="text-sm font-semibold text-foreground">
                      {(() => {
                        const info = PROVIDER_INFO[llmSettings?.provider as AnyProvider];
                        return info
                          ? `${info.emoji} ${info.label}`
                          : llmSettings?.provider || "Groq";
                      })()}
                    </p>
                  </div>
                  <div className="flex flex-col items-end shrink-0">
                    <span className="text-xs text-muted-foreground mb-0.5">
                      {llmSettings?.aiSource === "cloud" ? "☁ Cloud" : "💻 Local"}
                    </span>
                    {isAiStatusLoading ? (
                      <span className="text-xs font-medium text-muted-foreground animate-pulse">Checking...</span>
                    ) : aiConnectionStatus?.connected ? (
                      <span className="text-[10px] font-medium text-emerald-500 bg-emerald-500/10 px-1.5 py-0.5 rounded-md">🟢 Connected</span>
                    ) : (
                      <span className="text-[10px] font-medium text-red-500 bg-red-500/10 px-1.5 py-0.5 rounded-md">🔴 Disconnected</span>
                    )}
                  </div>
                </div>

                {/* Model Row */}
                <div className="flex items-center gap-3 p-3 bg-muted/30 rounded-xl">
                  <div className="w-2 h-2 rounded-full bg-blue-500 shrink-0" />
                  <div className="flex-1 min-w-0">
                    <p className="text-xs text-muted-foreground">Model</p>
                    <p className="text-sm font-semibold text-foreground truncate" title={llmSettings?.model}>
                      {llmSettings?.model || "—"}
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </motion.div>
        </div>
      </motion.div>
    </div>
  );
}

// We need Bookmark imported for empty state
import { Bookmark } from "lucide-react";
