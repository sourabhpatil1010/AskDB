import { useState, useEffect, useCallback } from "react";
import { useSearchParams, useNavigate } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import {
  Search,
  Sparkles,
  Loader2,
  AlertTriangle,
  ChevronDown,
  ArrowRight,
  MessageSquare,
  FileJson,
  Database,
  Table2,
  Bookmark,
  RefreshCw,
  CheckCircle2,
  BarChart3,
} from "lucide-react";
import { toast } from "sonner";
import { searchApi } from "@/services/search.service";
import { useAppStore } from "@/store/appStore";
import type { SearchResponse } from "@/types/search";
import { JsonViewer } from "@/components/viewers/JsonViewer";
import { SqlViewer } from "@/components/viewers/SqlViewer";
import { ResultTable } from "@/components/viewers/ResultTable";

const examplePrompts = [
  { text: "Show all departments", icon: "🏢" },
  { text: "Top 10 highest salaries", icon: "💰" },
  { text: "Employees hired this year", icon: "👥" },
  { text: "Average salary by department", icon: "📊" },
  { text: "Projects ending next month", icon: "📅" },
  { text: "Count employees by office", icon: "🏠" },
];

const pipelineSteps = [
  { key: "nl", label: "Natural Language", subtitle: "Understand your question", icon: MessageSquare },
  { key: "json", label: "Structured JSON", subtitle: "Parse query structure", icon: FileJson },
  { key: "sql", label: "SQL Query", subtitle: "Generate SQL statement", icon: Database },
  { key: "results", label: "Results", subtitle: "Execute and return data", icon: Table2 },
];

export default function AISearchPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();
  const [query, setQuery] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [result, setResult] = useState<SearchResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [activeStep, setActiveStep] = useState(-1);
  const [activeTab, setActiveTab] = useState<"results" | "sql" | "json" | "info">("results");
  const addSavedQuery = useAppStore((s) => s.addSavedQuery);

  const handleSearch = useCallback(async (searchQuery: string) => {
    if (!searchQuery.trim()) return;
    setQuery(searchQuery);
    setIsLoading(true);
    setError(null);
    setResult(null);
    setActiveStep(0);

    // Animate through steps
    const stepTimers: ReturnType<typeof setTimeout>[] = [];
    stepTimers.push(setTimeout(() => setActiveStep(1), 600));
    stepTimers.push(setTimeout(() => setActiveStep(2), 1200));

    try {
      const data = await searchApi.executeSearch({ query: searchQuery });
      stepTimers.forEach(clearTimeout);
      setActiveStep(3);
      setResult(data);
      setActiveTab("results");
      toast.success(`Query executed successfully`, {
        description: `${data.row_count} rows returned in ${data.execution_time_ms}ms`,
      });
      setSearchParams({});
    } catch (err: any) {
      stepTimers.forEach(clearTimeout);
      setActiveStep(-1);
      const errorMessage =
        err.response?.data?.detail || err.message || "An unexpected error occurred.";
      setError(errorMessage);
      toast.error("Query failed", { description: errorMessage });
    } finally {
      setIsLoading(false);
    }
  }, [setSearchParams]);

  useEffect(() => {
    const q = searchParams.get("q");
    if (q) {
      setQuery(q);
      handleSearch(q);
    }
  }, []);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (query.trim() && !isLoading) {
      handleSearch(query.trim());
    }
  };

  const handleSaveQuery = () => {
    if (result && query) {
      addSavedQuery({ query, sql: result.generated_sql });
      toast.success("Query saved!");
    }
  };

  const handleRetry = () => {
    if (query) handleSearch(query);
  };

  return (
    <div className="min-h-screen p-6 lg:p-8">
      <div className="max-w-[1400px] mx-auto">
        {/* Search Area */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className={`transition-all duration-500 ${
            result || error ? "mb-8" : "flex flex-col items-center justify-center min-h-[50vh]"
          }`}
        >
          {!result && !error && !isLoading && (
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              className="text-center mb-10"
            >
              <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-violet-500 to-indigo-600 flex items-center justify-center mx-auto mb-6 shadow-xl shadow-violet-500/25">
                <Sparkles className="w-8 h-8 text-white" />
              </div>
              <h1 className="text-3xl md:text-4xl font-bold text-foreground tracking-tight mb-3">
                Ask your database anything...
              </h1>
              <p className="text-muted-foreground text-base max-w-lg mx-auto">
                Type a natural language question and let AI generate the SQL query for you.
              </p>
            </motion.div>
          )}

          {/* Search Input */}
          <form onSubmit={handleSubmit} className="w-full max-w-3xl mx-auto relative group">
            <div className="absolute -inset-1 bg-gradient-to-r from-violet-500/20 via-indigo-500/20 to-purple-500/20 rounded-2xl blur-lg opacity-0 group-focus-within:opacity-100 transition-opacity duration-500" />
            <div className="relative flex items-center bg-card border border-border rounded-2xl shadow-sm group-focus-within:shadow-lg group-focus-within:border-primary/30 transition-all duration-300 overflow-hidden">
              <div className="pl-5 flex items-center text-muted-foreground">
                <Search className="w-5 h-5" />
              </div>
              <input
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Ask a question about your database..."
                className="w-full py-4 px-4 bg-transparent text-foreground placeholder-muted-foreground focus:outline-none text-base"
                disabled={isLoading}
                id="search-input"
                aria-label="Database query input"
              />
              <button
                type="submit"
                disabled={!query.trim() || isLoading}
                className="m-2 px-5 py-2.5 bg-gradient-to-r from-violet-500 to-indigo-600 hover:from-violet-600 hover:to-indigo-700 text-white font-medium rounded-xl transition-all disabled:opacity-40 disabled:cursor-not-allowed flex items-center gap-2 shadow-md shadow-violet-500/20 shrink-0"
                aria-label="Execute search"
              >
                {isLoading ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <Sparkles className="w-4 h-4" />
                )}
                <span className="hidden sm:inline">Search</span>
              </button>
            </div>
          </form>

          {/* Example Prompts */}
          {!result && !error && !isLoading && (
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.2 }}
              className="mt-8 w-full max-w-3xl mx-auto"
            >
              <p className="text-xs text-muted-foreground font-medium mb-3 text-center">
                Try these examples
              </p>
              <div className="flex flex-wrap justify-center gap-2">
                {examplePrompts.map((prompt) => (
                  <button
                    key={prompt.text}
                    onClick={() => {
                      setQuery(prompt.text);
                      handleSearch(prompt.text);
                    }}
                    className="px-3 py-2 text-sm bg-card border border-border rounded-xl hover:bg-muted/50 hover:border-primary/20 transition-all text-foreground flex items-center gap-2"
                  >
                    <span>{prompt.icon}</span>
                    <span>{prompt.text}</span>
                  </button>
                ))}
              </div>
            </motion.div>
          )}
        </motion.div>

        {/* Pipeline Progress */}
        <AnimatePresence>
          {(isLoading || result) && (
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              className="mb-8"
            >
              <div className="bg-card border border-border rounded-2xl p-6">
                <h3 className="text-sm font-semibold text-foreground mb-4 flex items-center gap-2">
                  <BarChart3 className="w-4 h-4 text-primary" />
                  Query Pipeline
                </h3>
                <div className="flex items-center justify-between gap-2">
                  {pipelineSteps.map((step, idx) => {
                    const Icon = step.icon;
                    const isComplete = activeStep > idx;
                    const isCurrent = activeStep === idx;
                    const isPending = activeStep < idx;
                    return (
                      <div key={step.key} className="flex items-center flex-1">
                        <div className="flex flex-col items-center flex-1">
                          <motion.div
                            animate={{
                              scale: isCurrent ? 1.1 : 1,
                              borderColor: isComplete
                                ? "hsl(262, 83%, 58%)"
                                : isCurrent
                                ? "hsl(262, 83%, 58%)"
                                : "hsl(var(--border))",
                            }}
                            className={`w-10 h-10 rounded-xl border-2 flex items-center justify-center mb-2 transition-colors ${
                              isComplete
                                ? "bg-primary text-white border-primary"
                                : isCurrent
                                ? "bg-primary/10 text-primary border-primary"
                                : "bg-muted/30 text-muted-foreground border-border"
                            }`}
                          >
                            {isComplete ? (
                              <CheckCircle2 className="w-5 h-5" />
                            ) : isCurrent && isLoading ? (
                              <Loader2 className="w-5 h-5 animate-spin" />
                            ) : (
                              <Icon className="w-5 h-5" />
                            )}
                          </motion.div>
                          <p
                            className={`text-xs font-medium text-center ${
                              isComplete || isCurrent
                                ? "text-foreground"
                                : "text-muted-foreground"
                            }`}
                          >
                            {step.label}
                          </p>
                          <p className="text-[10px] text-muted-foreground text-center hidden sm:block">
                            {step.subtitle}
                          </p>
                        </div>
                        {idx < pipelineSteps.length - 1 && (
                          <div className="flex-shrink-0 w-8 lg:w-16 mx-1">
                            <div
                              className={`h-0.5 w-full rounded-full transition-colors duration-300 ${
                                isComplete ? "bg-primary" : "bg-border"
                              }`}
                            />
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Error State */}
        <AnimatePresence>
          {error && (
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              className="mb-8"
            >
              <div className="bg-destructive/5 border border-destructive/20 rounded-2xl p-6">
                <div className="flex items-start gap-4">
                  <div className="w-10 h-10 rounded-xl bg-destructive/10 flex items-center justify-center shrink-0">
                    <AlertTriangle className="w-5 h-5 text-destructive" />
                  </div>
                  <div className="flex-1">
                    <h3 className="font-semibold text-destructive mb-1">Failed to execute query</h3>
                    <p className="text-sm text-muted-foreground mb-4">{error}</p>
                    <div className="flex items-center gap-3">
                      <button
                        onClick={handleRetry}
                        className="px-4 py-2 bg-primary text-white text-sm font-medium rounded-xl hover:bg-primary/90 transition-colors flex items-center gap-2"
                      >
                        <RefreshCw className="w-4 h-4" />
                        Try Again
                      </button>
                      <details className="text-sm">
                        <summary className="text-muted-foreground cursor-pointer hover:text-foreground transition-colors">
                          View Details
                        </summary>
                        <pre className="mt-2 p-3 bg-muted/50 rounded-lg text-xs text-muted-foreground overflow-auto font-mono">
                          {error}
                        </pre>
                      </details>
                    </div>
                  </div>
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Results */}
        <AnimatePresence>
          {result && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
            >
              {/* Result Header */}
              <div className="flex flex-wrap items-center justify-between gap-4 mb-4">
                <div className="flex items-center gap-3">
                  <h2 className="text-lg font-semibold text-foreground">{query}</h2>
                  <span className="px-2.5 py-1 text-xs font-medium bg-emerald-500/10 text-emerald-500 rounded-lg">
                    Success
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-xs text-muted-foreground bg-muted/50 px-3 py-1.5 rounded-lg">
                    ⏱ {result.execution_time_ms}ms
                  </span>
                  <span className="text-xs text-muted-foreground bg-muted/50 px-3 py-1.5 rounded-lg">
                    {result.row_count} rows
                  </span>
                  <button
                    onClick={handleSaveQuery}
                    className="px-3 py-1.5 text-xs font-medium bg-primary/10 text-primary rounded-lg hover:bg-primary/20 transition-colors flex items-center gap-1.5"
                    aria-label="Save this query"
                  >
                    <Bookmark className="w-3.5 h-3.5" />
                    Save
                  </button>
                </div>
              </div>

              {/* Tabs */}
              <div className="flex items-center gap-1 mb-4 bg-muted/30 p-1 rounded-xl w-fit">
                {(["results", "sql", "json", "info"] as const).map((tab) => (
                  <button
                    key={tab}
                    onClick={() => setActiveTab(tab)}
                    className={`px-4 py-2 text-sm font-medium rounded-lg transition-all ${
                      activeTab === tab
                        ? "bg-card text-foreground shadow-sm"
                        : "text-muted-foreground hover:text-foreground"
                    }`}
                  >
                    {tab === "results"
                      ? "Results"
                      : tab === "sql"
                      ? "SQL"
                      : tab === "json"
                      ? "JSON"
                      : "Info"}
                  </button>
                ))}
              </div>

              {/* Tab Content */}
              <AnimatePresence mode="wait">
                {activeTab === "results" && (
                  <motion.div
                    key="results"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                  >
                    <ResultTable
                      columns={result.columns || []}
                      rows={result.rows || []}
                      executionTimeMs={result.execution_time_ms}
                      rowCount={result.row_count}
                    />
                  </motion.div>
                )}
                {activeTab === "sql" && (
                  <motion.div
                    key="sql"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                  >
                    <SqlViewer sql={result.generated_sql || ""} />
                  </motion.div>
                )}
                {activeTab === "json" && (
                  <motion.div
                    key="json"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                  >
                    <JsonViewer data={result.structured_json} />
                  </motion.div>
                )}
                {activeTab === "info" && (
                  <motion.div
                    key="info"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                  >
                    <div className="bg-card border border-border rounded-2xl p-6 space-y-4">
                      <h3 className="font-semibold text-foreground">Query Details</h3>
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                        <div className="bg-muted/30 rounded-xl p-4">
                          <p className="text-xs text-muted-foreground mb-1">Question</p>
                          <p className="text-sm font-medium text-foreground">
                            {result.question || query}
                          </p>
                        </div>
                        <div className="bg-muted/30 rounded-xl p-4">
                          <p className="text-xs text-muted-foreground mb-1">Execution Time</p>
                          <p className="text-sm font-medium text-foreground">
                            {result.execution_time_ms}ms
                          </p>
                        </div>
                        <div className="bg-muted/30 rounded-xl p-4">
                          <p className="text-xs text-muted-foreground mb-1">Rows Returned</p>
                          <p className="text-sm font-medium text-foreground">
                            {result.row_count}
                          </p>
                        </div>
                        <div className="bg-muted/30 rounded-xl p-4">
                          <p className="text-xs text-muted-foreground mb-1">Columns</p>
                          <p className="text-sm font-medium text-foreground">
                            {result.columns?.length || 0}
                          </p>
                        </div>
                      </div>
                      {result.parameters &&
                        Object.keys(result.parameters).length > 0 && (
                          <div className="bg-muted/30 rounded-xl p-4">
                            <p className="text-xs text-muted-foreground mb-2">Parameters</p>
                            <pre className="text-xs font-mono text-foreground">
                              {JSON.stringify(result.parameters, null, 2)}
                            </pre>
                          </div>
                        )}
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Loading skeleton for results area */}
        {isLoading && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="space-y-4"
          >
            <div className="bg-card border border-border rounded-2xl p-6">
              <div className="flex items-center gap-3 mb-4">
                <div className="flex items-center gap-2">
                  <div className="w-2 h-2 rounded-full bg-primary animate-typing-dot" style={{ animationDelay: "0s" }} />
                  <div className="w-2 h-2 rounded-full bg-primary animate-typing-dot" style={{ animationDelay: "0.2s" }} />
                  <div className="w-2 h-2 rounded-full bg-primary animate-typing-dot" style={{ animationDelay: "0.4s" }} />
                </div>
                <span className="text-sm text-muted-foreground">Generating SQL query...</span>
              </div>
              <div className="space-y-3">
                <div className="h-4 w-3/4 skeleton-shimmer rounded" />
                <div className="h-4 w-1/2 skeleton-shimmer rounded" />
                <div className="h-4 w-5/6 skeleton-shimmer rounded" />
              </div>
            </div>
          </motion.div>
        )}
      </div>
    </div>
  );
}
