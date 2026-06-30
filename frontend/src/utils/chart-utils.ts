// ─── AskDB Purple-primary chart color palette ────────────────────────────────

export const CHART_COLORS = [
  "#7c3aed", // violet-700  (primary)
  "#6366f1", // indigo-500
  "#06b6d4", // cyan-500
  "#10b981", // emerald-500
  "#f59e0b", // amber-500
  "#ef4444", // red-500
  "#ec4899", // pink-500
  "#8b5cf6", // violet-500
  "#3b82f6", // blue-500
  "#84cc16", // lime-500
  "#f97316", // orange-500
  "#14b8a6", // teal-500
];

export function getChartColor(index: number): string {
  return CHART_COLORS[index % CHART_COLORS.length];
}

// ─── Number / label formatting (re-exported from canonical formatters) ────────
//
// formatNumber  → "1,15,244.73"  (en-IN locale, 2 dp, thousands-separated)
// truncateLabel → clip long axis tick labels with ellipsis
//
export { formatCompactNumber as formatNumber } from "@/utils/formatters";
export { truncateText as truncateLabel } from "@/utils/formatters";


// ─── SVG Export ───────────────────────────────────────────────────────────────

export function exportSVG(containerId: string, filename = "chart.svg"): void {
  const el = document.getElementById(containerId);
  if (!el) return;
  const svg = el.querySelector("svg");
  if (!svg) return;

  // Clone and add a white/transparent background rect
  const clone = svg.cloneNode(true) as SVGElement;
  const ns = "http://www.w3.org/2000/svg";
  const bg = document.createElementNS(ns, "rect");
  bg.setAttribute("width", "100%");
  bg.setAttribute("height", "100%");
  bg.setAttribute("fill", "transparent");
  clone.insertBefore(bg, clone.firstChild);

  const serializer = new XMLSerializer();
  const svgString = serializer.serializeToString(clone);
  const blob = new Blob([svgString], { type: "image/svg+xml;charset=utf-8" });
  triggerDownload(URL.createObjectURL(blob), filename);
}

// ─── PNG Export ───────────────────────────────────────────────────────────────

export function exportPNG(containerId: string, filename = "chart.png"): void {
  const el = document.getElementById(containerId);
  if (!el) return;
  const svg = el.querySelector("svg");
  if (!svg) return;

  const serializer = new XMLSerializer();
  const svgString = serializer.serializeToString(svg);
  const canvas = document.createElement("canvas");
  const bbox = svg.getBoundingClientRect();
  const scale = window.devicePixelRatio || 2;
  canvas.width = bbox.width * scale;
  canvas.height = bbox.height * scale;

  const ctx = canvas.getContext("2d")!;
  ctx.scale(scale, scale);

  const img = new Image();
  img.onload = () => {
    ctx.fillStyle = "transparent";
    ctx.drawImage(img, 0, 0);
    triggerDownload(canvas.toDataURL("image/png"), filename);
    URL.revokeObjectURL(img.src);
  };
  img.src = "data:image/svg+xml;base64," + btoa(unescape(encodeURIComponent(svgString)));
}

// ─── CSV Export ───────────────────────────────────────────────────────────────

export function exportCSV(
  data: Record<string, any>[],
  filename = "chart-data.csv",
): void {
  if (!data.length) return;
  const keys = Object.keys(data[0]);
  const header = keys.join(",");
  const rows = data.map((row) =>
    keys.map((k) => `"${String(row[k] ?? "").replace(/"/g, '""')}"`).join(","),
  );
  const csv = [header, ...rows].join("\n");
  const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
  triggerDownload(URL.createObjectURL(blob), filename);
}

// ─── Excel Export ─────────────────────────────────────────────────────────────

export async function exportExcel(
  data: Record<string, any>[],
  filename = "chart-data.xlsx",
): Promise<void> {
  const XLSX = await import("xlsx");
  const ws = XLSX.utils.json_to_sheet(data);
  const wb = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(wb, ws, "Chart Data");
  XLSX.writeFile(wb, filename);
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

function triggerDownload(href: string, filename: string): void {
  const a = document.createElement("a");
  a.href = href;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  setTimeout(() => URL.revokeObjectURL(href), 1000);
}
