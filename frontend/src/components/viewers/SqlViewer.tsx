import { useState, useRef, useEffect } from "react";
import {
  Copy,
  Check,
  Download,
  Database,
  ChevronDown,
  ChevronRight,
} from "lucide-react";
import { toast } from "sonner";
import { copyToClipboard, downloadFile } from "@/lib/utils";

interface SqlViewerProps {
  sql: string;
  isLoading?: boolean;
}

export function SqlViewer({ sql, isLoading }: SqlViewerProps) {
  const [copied, setCopied] = useState(false);
  const [expanded, setExpanded] = useState(true);
  const [useMonaco, setUseMonaco] = useState(false);
  const [MonacoEditor, setMonacoEditor] = useState<any>(null);

  // Lazy load Monaco
  useEffect(() => {
    if (expanded && sql) {
      import("@monaco-editor/react").then((mod) => {
        setMonacoEditor(() => mod.default);
        setUseMonaco(true);
      }).catch(() => {
        setUseMonaco(false);
      });
    }
  }, [expanded, sql]);

  const handleCopy = async () => {
    await copyToClipboard(sql);
    setCopied(true);
    toast.success("SQL copied to clipboard");
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDownload = () => {
    downloadFile(sql, "generated_query.sql", "text/sql");
    toast.success("SQL downloaded");
  };

  if (isLoading) {
    return (
      <div className="bg-card border border-border rounded-2xl overflow-hidden animate-pulse">
        <div className="flex items-center px-5 py-4 border-b border-border">
          <div className="h-4 w-32 skeleton-shimmer rounded" />
        </div>
        <div className="p-5 space-y-3">
          <div className="h-4 w-5/6 skeleton-shimmer rounded" />
          <div className="h-4 w-3/4 skeleton-shimmer rounded" />
          <div className="h-4 w-2/3 skeleton-shimmer rounded" />
        </div>
      </div>
    );
  }

  if (!sql) return null;

  const lineCount = sql.split("\n").length;
  const editorHeight = Math.max(120, Math.min(lineCount * 22 + 40, 400));

  return (
    <div className="bg-card border border-border rounded-2xl overflow-hidden transition-all duration-300 hover:shadow-md">
      <div className="flex items-center justify-between px-5 py-3.5 border-b border-border bg-muted/20">
        <button
          onClick={() => setExpanded(!expanded)}
          className="flex items-center gap-2 text-sm font-semibold text-foreground hover:text-primary transition-colors"
          aria-expanded={expanded}
          aria-label={`${expanded ? "Collapse" : "Expand"} SQL viewer`}
        >
          {expanded ? (
            <ChevronDown className="w-4 h-4" />
          ) : (
            <ChevronRight className="w-4 h-4" />
          )}
          <Database className="w-4 h-4 text-violet-500" />
          Generated SQL
        </button>
        <div className="flex items-center gap-1">
          <button
            onClick={handleDownload}
            className="p-1.5 rounded-lg hover:bg-muted text-muted-foreground hover:text-foreground transition-all"
            title="Download SQL"
            aria-label="Download SQL"
          >
            <Download className="w-4 h-4" />
          </button>
          <button
            onClick={handleCopy}
            className="p-1.5 rounded-lg hover:bg-muted text-muted-foreground hover:text-foreground transition-all"
            title="Copy SQL"
            aria-label="Copy SQL to clipboard"
          >
            {copied ? (
              <Check className="w-4 h-4 text-emerald-500" />
            ) : (
              <Copy className="w-4 h-4" />
            )}
          </button>
        </div>
      </div>

      {expanded && (
        <div className="overflow-hidden" style={{ height: editorHeight }}>
          {useMonaco && MonacoEditor ? (
            <MonacoEditor
              height={editorHeight}
              language="sql"
              value={sql}
              theme="vs-dark"
              options={{
                readOnly: true,
                minimap: { enabled: false },
                scrollBeyondLastLine: false,
                fontSize: 13,
                fontFamily: "'JetBrains Mono', 'Fira Code', monospace",
                lineNumbers: "on",
                renderLineHighlight: "none",
                padding: { top: 16, bottom: 16 },
                overviewRulerLanes: 0,
                hideCursorInOverviewRuler: true,
                overviewRulerBorder: false,
                scrollbar: {
                  vertical: "auto",
                  horizontal: "auto",
                  verticalScrollbarSize: 6,
                  horizontalScrollbarSize: 6,
                },
                wordWrap: "on",
                contextmenu: false,
                domReadOnly: true,
              }}
            />
          ) : (
            <pre className="p-5 text-sm font-mono text-foreground overflow-auto custom-scrollbar bg-[#1e1e2e] h-full">
              <code>{sql}</code>
            </pre>
          )}
        </div>
      )}
    </div>
  );
}
