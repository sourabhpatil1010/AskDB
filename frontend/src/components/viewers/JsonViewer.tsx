import { useState, useMemo } from "react";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { oneDark } from "react-syntax-highlighter/dist/esm/styles/prism";
import {
  Copy,
  Check,
  ChevronDown,
  ChevronRight,
  Download,
  FileJson,
} from "lucide-react";
import { toast } from "sonner";
import { copyToClipboard, downloadFile } from "@/lib/utils";

interface JsonViewerProps {
  data: any;
  title?: string;
  isLoading?: boolean;
}

export function JsonViewer({ data, title = "Structured JSON", isLoading }: JsonViewerProps) {
  const [copied, setCopied] = useState(false);
  const [expanded, setExpanded] = useState(true);

  const jsonString = useMemo(() => JSON.stringify(data, null, 2), [data]);

  const handleCopy = async () => {
    await copyToClipboard(jsonString);
    setCopied(true);
    toast.success("JSON copied to clipboard");
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDownload = () => {
    downloadFile(jsonString, "structured_query.json", "application/json");
    toast.success("JSON downloaded");
  };

  if (isLoading) {
    return (
      <div className="bg-card border border-border rounded-2xl overflow-hidden animate-pulse">
        <div className="flex items-center px-5 py-4 border-b border-border">
          <div className="h-4 w-32 skeleton-shimmer rounded" />
        </div>
        <div className="p-5 space-y-3">
          <div className="h-4 w-3/4 skeleton-shimmer rounded" />
          <div className="h-4 w-1/2 skeleton-shimmer rounded" />
          <div className="h-4 w-5/6 skeleton-shimmer rounded" />
          <div className="h-4 w-2/3 skeleton-shimmer rounded" />
        </div>
      </div>
    );
  }

  if (!data) return null;

  return (
    <div className="bg-card border border-border rounded-2xl overflow-hidden transition-all duration-300 hover:shadow-md">
      <div className="flex items-center justify-between px-5 py-3.5 border-b border-border bg-muted/20">
        <button
          onClick={() => setExpanded(!expanded)}
          className="flex items-center gap-2 text-sm font-semibold text-foreground hover:text-primary transition-colors"
          aria-expanded={expanded}
          aria-label={`${expanded ? "Collapse" : "Expand"} ${title}`}
        >
          {expanded ? (
            <ChevronDown className="w-4 h-4" />
          ) : (
            <ChevronRight className="w-4 h-4" />
          )}
          <FileJson className="w-4 h-4 text-primary" />
          {title}
        </button>
        <div className="flex items-center gap-1">
          <button
            onClick={handleDownload}
            className="p-1.5 rounded-lg hover:bg-muted text-muted-foreground hover:text-foreground transition-all"
            title="Download JSON"
            aria-label="Download JSON"
          >
            <Download className="w-4 h-4" />
          </button>
          <button
            onClick={handleCopy}
            className="p-1.5 rounded-lg hover:bg-muted text-muted-foreground hover:text-foreground transition-all"
            title="Copy to clipboard"
            aria-label="Copy JSON to clipboard"
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
        <div className="max-h-[500px] overflow-auto custom-scrollbar bg-[#1e1e2e]">
          <SyntaxHighlighter
            language="json"
            style={oneDark}
            customStyle={{
              margin: 0,
              padding: "1.25rem",
              background: "transparent",
              fontSize: "13px",
            }}
            codeTagProps={{ className: "font-mono" }}
            showLineNumbers
            lineNumberStyle={{ color: "hsl(var(--muted-foreground) / 0.3)", fontSize: "12px" }}
          >
            {jsonString}
          </SyntaxHighlighter>
        </div>
      )}
    </div>
  );
}
