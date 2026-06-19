import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { motion, AnimatePresence } from "framer-motion";
import {
  Clock,
  Trash2,
  Search,
  Play,
  CheckCircle2,
  XCircle,
  Filter,
  Calendar,
} from "lucide-react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { historyApi } from "@/services/history.service";
import { formatDate, formatMs } from "@/lib/utils";

export default function HistoryPage() {
  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState<"all" | "success">("all");
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const { data: historyData, isLoading } = useQuery({
    queryKey: ["history"],
    queryFn: async () => {
      const result = await historyApi.getAll();
      return result.data;
    },
  });

  const deleteOne = useMutation({
    mutationFn: historyApi.deleteOne,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["history"] });
      toast.success("Item deleted from history");
    },
    onError: () => toast.error("Failed to delete history item"),
  });

  const deleteAll = useMutation({
    mutationFn: historyApi.deleteAll,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["history"] });
      toast.success("All search history cleared");
    },
    onError: () => toast.error("Failed to clear history"),
  });

  const handleDeleteAll = () => {
    if (!window.confirm("Are you sure you want to delete all search history?"))
      return;
    deleteAll.mutate();
  };

  const [expandedId, setExpandedId] = useState<string | null>(null);

  const history = historyData || [];
  const filteredHistory = history.filter((h) =>
    h.natural_language.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="p-6 lg:p-8 max-w-[1200px] mx-auto">
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
      >
        {/* Header */}
        <div className="flex flex-col md:flex-row items-start md:items-center justify-between mb-8">
          <div>
            <h1 className="text-2xl font-bold text-foreground flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-blue-500 to-cyan-500 flex items-center justify-center shadow-lg">
                <Clock className="w-5 h-5 text-white" />
              </div>
              Query History
            </h1>
            <p className="text-muted-foreground mt-2 text-sm">
              View and rerun your previous AI-powered searches.
            </p>
          </div>
          {history.length > 0 && (
            <button
              onClick={handleDeleteAll}
              disabled={deleteAll.isPending}
              className="mt-4 md:mt-0 flex items-center gap-2 px-4 py-2 text-sm text-destructive bg-destructive/5 hover:bg-destructive/10 rounded-xl transition-colors border border-destructive/10"
            >
              <Trash2 className="w-4 h-4" />
              Clear All
            </button>
          )}
        </div>

        {/* Search & Filters */}
        <div className="flex items-center gap-3 mb-6">
          <div className="relative flex-1 max-w-md">
            <Search className="w-4 h-4 absolute left-3.5 top-1/2 -translate-y-1/2 text-muted-foreground" />
            <input
              type="text"
              placeholder="Search history..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-10 pr-4 py-2.5 bg-card border border-border rounded-xl focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary/30 text-sm transition-all"
              aria-label="Filter history"
            />
          </div>
        </div>

        {/* Content */}
        {isLoading ? (
          <div className="space-y-3">
            {Array.from({ length: 5 }).map((_, i) => (
              <div
                key={i}
                className="bg-card border border-border rounded-2xl p-5 animate-pulse"
              >
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-xl skeleton-shimmer" />
                  <div className="flex-1 space-y-2">
                    <div className="h-4 w-3/4 skeleton-shimmer rounded" />
                    <div className="h-3 w-1/3 skeleton-shimmer rounded" />
                  </div>
                </div>
              </div>
            ))}
          </div>
        ) : filteredHistory.length === 0 ? (
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            className="text-center py-20 bg-card border border-border rounded-2xl"
          >
            <Clock className="w-12 h-12 text-muted-foreground/30 mx-auto mb-4" />
            <h3 className="text-lg font-semibold text-foreground mb-2">
              {searchQuery ? "No matching results" : "No search history yet"}
            </h3>
            <p className="text-sm text-muted-foreground max-w-sm mx-auto">
              {searchQuery
                ? "Try adjusting your search terms"
                : "Your AI-powered database searches will appear here."}
            </p>
            {!searchQuery && (
              <button
                onClick={() => navigate("/search")}
                className="mt-6 px-5 py-2.5 bg-primary text-white text-sm font-medium rounded-xl hover:bg-primary/90 transition-colors"
              >
                Start Searching
              </button>
            )}
          </motion.div>
        ) : (
          <div className="space-y-3">
            <AnimatePresence>
              {filteredHistory.map((item, idx) => (
                <motion.div
                  key={item.id}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, scale: 0.95 }}
                  transition={{ delay: idx * 0.03 }}
                  className={`group bg-card border rounded-2xl p-5 hover:shadow-md transition-all duration-300 cursor-pointer ${
                    expandedId === item.id ? "border-primary/30" : "border-border hover:border-primary/10"
                  }`}
                  onClick={() => setExpandedId(expandedId === item.id ? null : item.id)}
                >
                  <div className="flex flex-col sm:flex-row items-start sm:items-center gap-4">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-2 flex-wrap">
                        {item.status === "SUCCESS" ? (
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 text-xs font-medium bg-emerald-500/10 text-emerald-500 rounded-md">
                            <CheckCircle2 className="w-3 h-3" />
                            Success
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 text-xs font-medium bg-red-500/10 text-red-500 rounded-md">
                            <XCircle className="w-3 h-3" />
                            {item.status}
                          </span>
                        )}
                        <span className="text-xs text-muted-foreground flex items-center gap-1">
                          <Calendar className="w-3 h-3" />
                          {new Date(item.created_at).toLocaleDateString()}{" "}
                          {new Date(item.created_at).toLocaleTimeString()}
                        </span>
                        <span className="text-xs text-muted-foreground">
                          ⏱ {formatMs(item.execution_time_ms || 0)}
                        </span>
                      </div>
                      <h3 className="text-base font-medium text-foreground group-hover:text-primary transition-colors line-clamp-2">
                        {item.natural_language}
                      </h3>
                      
                      {expandedId === item.id && item.error_message && (
                        <motion.div 
                          initial={{ opacity: 0, height: 0 }}
                          animate={{ opacity: 1, height: "auto" }}
                          className="mt-4 p-3 bg-red-500/5 border border-red-500/10 rounded-xl"
                        >
                          <p className="text-sm font-medium text-red-500 mb-1 flex items-center gap-2">
                            <XCircle className="w-4 h-4" /> Error Details
                          </p>
                          <p className="text-xs text-red-400 font-mono break-all bg-background/50 p-2 rounded-lg">
                            {item.error_message}
                          </p>
                        </motion.div>
                      )}
                    </div>
                    <div className="flex items-center gap-2 shrink-0" onClick={e => e.stopPropagation()}>
                      <button
                        onClick={() =>
                          navigate(
                            `/search?q=${encodeURIComponent(
                              item.natural_language
                            )}`
                          )
                        }
                        className="flex items-center gap-2 px-4 py-2 bg-primary text-white text-sm font-medium rounded-xl hover:bg-primary/90 transition-colors"
                      >
                        <Play className="w-4 h-4" />
                        Rerun
                      </button>
                      <button
                        onClick={() => deleteOne.mutate(item.id)}
                        disabled={deleteOne.isPending}
                        className="p-2 text-muted-foreground hover:text-destructive hover:bg-destructive/5 rounded-xl transition-colors"
                        title="Delete"
                        aria-label="Delete history item"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                </motion.div>
              ))}
            </AnimatePresence>
          </div>
        )}
      </motion.div>
    </div>
  );
}
