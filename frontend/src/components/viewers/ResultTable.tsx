import { useState, useMemo } from "react";
import {
  useReactTable,
  getCoreRowModel,
  getSortedRowModel,
  getFilteredRowModel,
  getPaginationRowModel,
  flexRender,
  type ColumnDef,
  type SortingState,
  type ColumnFiltersState,
  type VisibilityState,
} from "@tanstack/react-table";
import {
  Table2,
  ChevronLeft,
  ChevronRight,
  ChevronsLeft,
  ChevronsRight,
  FileText,
  FileSpreadsheet,
  Search,
  ArrowUpDown,
  ArrowUp,
  ArrowDown,
  Copy,
  SearchX,
  Columns3,
  Eye,
  EyeOff,
} from "lucide-react";
import * as XLSX from "xlsx";
import { toast } from "sonner";
import { copyToClipboard, formatMs } from "@/lib/utils";

interface ResultTableProps {
  columns: string[];
  rows: any[];
  executionTimeMs?: number;
  rowCount?: number;
  isLoading?: boolean;
}

export function ResultTable({
  columns: columnNames,
  rows,
  executionTimeMs,
  rowCount,
  isLoading,
}: ResultTableProps) {
  const [sorting, setSorting] = useState<SortingState>([]);
  const [columnFilters, setColumnFilters] = useState<ColumnFiltersState>([]);
  const [globalFilter, setGlobalFilter] = useState("");
  const [columnVisibility, setColumnVisibility] = useState<VisibilityState>({});
  const [showColumnPicker, setShowColumnPicker] = useState(false);

  const columns = useMemo<ColumnDef<any>[]>(
    () =>
      columnNames.map((col) => ({
        accessorKey: col,
        header: ({ column }) => (
          <button
            onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}
            className="flex items-center gap-1.5 hover:text-foreground transition-colors font-semibold text-xs uppercase tracking-wider"
          >
            {col}
            {column.getIsSorted() === "asc" ? (
              <ArrowUp className="w-3 h-3" />
            ) : column.getIsSorted() === "desc" ? (
              <ArrowDown className="w-3 h-3" />
            ) : (
              <ArrowUpDown className="w-3 h-3 opacity-30" />
            )}
          </button>
        ),
        cell: ({ getValue }) => {
          const value = getValue();
          if (value === null)
            return <span className="text-muted-foreground/50 italic">null</span>;
          return <span className="text-sm">{String(value)}</span>;
        },
      })),
    [columnNames]
  );

  const table = useReactTable({
    data: rows,
    columns,
    state: {
      sorting,
      columnFilters,
      globalFilter,
      columnVisibility,
    },
    onSortingChange: setSorting,
    onColumnFiltersChange: setColumnFilters,
    onGlobalFilterChange: setGlobalFilter,
    onColumnVisibilityChange: setColumnVisibility,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
    initialState: {
      pagination: { pageSize: 10 },
    },
  });

  const handleCopyRow = async (row: any) => {
    const text = columnNames.map((col) => `${col}: ${row[col]}`).join("\n");
    await copyToClipboard(text);
    toast.success("Row copied to clipboard");
  };

  const handleDownloadCSV = () => {
    try {
      const visibleCols = columnNames.filter(
        (col) => columnVisibility[col] !== false
      );
      const header = visibleCols.join(",");
      const csvRows = rows.map((row) =>
        visibleCols
          .map((col) => `"${String(row[col] ?? "").replace(/"/g, '""')}"`)
          .join(",")
      );
      const csvString = [header, ...csvRows].join("\n");
      const blob = new Blob([csvString], { type: "text/csv;charset=utf-8;" });
      const link = document.createElement("a");
      link.href = URL.createObjectURL(blob);
      link.setAttribute("download", "query_results.csv");
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(link.href);
      toast.success("CSV downloaded");
    } catch {
      toast.error("Failed to download CSV");
    }
  };

  const handleDownloadExcel = () => {
    try {
      const worksheet = XLSX.utils.json_to_sheet(rows, {
        header: columnNames,
      });
      const workbook = XLSX.utils.book_new();
      XLSX.utils.book_append_sheet(workbook, worksheet, "Results");
      XLSX.writeFile(workbook, "query_results.xlsx");
      toast.success("Excel downloaded");
    } catch {
      toast.error("Failed to download Excel");
    }
  };

  if (isLoading) {
    return (
      <div className="bg-card border border-border rounded-2xl overflow-hidden animate-pulse">
        <div className="px-5 py-4 border-b border-border flex items-center justify-between">
          <div className="h-5 w-32 skeleton-shimmer rounded" />
          <div className="flex gap-2">
            <div className="h-8 w-20 skeleton-shimmer rounded-lg" />
            <div className="h-8 w-20 skeleton-shimmer rounded-lg" />
          </div>
        </div>
        <div className="p-5 space-y-3">
          <div className="h-8 w-full skeleton-shimmer rounded-lg" />
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="h-10 w-full skeleton-shimmer rounded-lg" />
          ))}
        </div>
      </div>
    );
  }

  if (!columnNames || columnNames.length === 0) return null;

  return (
    <div className="bg-card border border-border rounded-2xl overflow-hidden">
      {/* Header */}
      <div className="px-5 py-4 border-b border-border flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 text-foreground font-semibold text-sm">
            <Table2 className="w-4 h-4 text-primary" />
            Query Results
          </div>
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <span className="bg-muted/50 px-2 py-1 rounded-md">{rowCount ?? rows.length} rows</span>
            <span className="bg-muted/50 px-2 py-1 rounded-md">⏱ {formatMs(executionTimeMs)}</span>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {/* Search */}
          <div className="relative">
            <Search className="w-3.5 h-3.5 absolute left-2.5 top-1/2 -translate-y-1/2 text-muted-foreground" />
            <input
              type="text"
              placeholder="Search results..."
              value={globalFilter}
              onChange={(e) => setGlobalFilter(e.target.value)}
              className="pl-8 pr-3 py-1.5 text-xs bg-muted/30 border border-border rounded-lg focus:outline-none focus:ring-1 focus:ring-primary/30 w-40"
              aria-label="Search table results"
            />
          </div>
          {/* Column visibility */}
          <div className="relative">
            <button
              onClick={() => setShowColumnPicker(!showColumnPicker)}
              className="flex items-center gap-1.5 px-2.5 py-1.5 text-xs bg-muted/30 border border-border rounded-lg hover:bg-muted/50 transition-colors"
              aria-label="Toggle column visibility"
            >
              <Columns3 className="w-3.5 h-3.5" />
              Columns
            </button>
            {showColumnPicker && (
              <div className="absolute right-0 top-full mt-1 bg-card border border-border rounded-xl shadow-xl z-20 p-2 min-w-[180px] max-h-[300px] overflow-auto custom-scrollbar">
                {columnNames.map((col) => (
                  <label
                    key={col}
                    className="flex items-center gap-2 px-2 py-1.5 rounded-lg hover:bg-muted/30 cursor-pointer text-xs"
                  >
                    <input
                      type="checkbox"
                      checked={columnVisibility[col] !== false}
                      onChange={(e) =>
                        setColumnVisibility((prev) => ({
                          ...prev,
                          [col]: e.target.checked,
                        }))
                      }
                      className="rounded accent-primary"
                    />
                    <span className="text-foreground">{col}</span>
                  </label>
                ))}
              </div>
            )}
          </div>
          {/* Export */}
          <button
            onClick={handleDownloadCSV}
            disabled={rows.length === 0}
            className="flex items-center gap-1.5 px-2.5 py-1.5 text-xs bg-muted/30 border border-border rounded-lg hover:bg-muted/50 transition-colors disabled:opacity-40"
            aria-label="Export as CSV"
          >
            <FileText className="w-3.5 h-3.5" />
            CSV
          </button>
          <button
            onClick={handleDownloadExcel}
            disabled={rows.length === 0}
            className="flex items-center gap-1.5 px-2.5 py-1.5 text-xs bg-muted/30 border border-border rounded-lg hover:bg-muted/50 transition-colors disabled:opacity-40"
            aria-label="Export as Excel"
          >
            <FileSpreadsheet className="w-3.5 h-3.5" />
            Excel
          </button>
        </div>
      </div>

      {/* Table */}
      <div className="overflow-x-auto overflow-y-auto custom-scrollbar max-h-[600px]">
        {rows.length === 0 ? (
          <div className="flex flex-col items-center justify-center p-16 text-muted-foreground">
            <SearchX className="w-12 h-12 mb-4 opacity-30" />
            <p className="text-base font-medium text-foreground">No records found</p>
            <p className="text-sm mt-1 text-center">
              Your query executed successfully but returned zero rows.
            </p>
          </div>
        ) : (
          <table className="w-full text-sm text-left">
            <thead className="text-xs text-muted-foreground bg-muted/20 sticky top-0 z-10">
              {table.getHeaderGroups().map((headerGroup) => (
                <tr key={headerGroup.id}>
                  <th className="px-4 py-3 font-semibold w-10 text-center">#</th>
                  {headerGroup.headers.map((header) => (
                    <th
                      key={header.id}
                      className="px-4 py-3 whitespace-nowrap"
                    >
                      {header.isPlaceholder
                        ? null
                        : flexRender(
                            header.column.columnDef.header,
                            header.getContext()
                          )}
                    </th>
                  ))}
                  <th className="px-4 py-3 w-10" />
                </tr>
              ))}
            </thead>
            <tbody className="divide-y divide-border">
              {table.getRowModel().rows.map((row, idx) => (
                <tr
                  key={row.id}
                  className="hover:bg-muted/20 transition-colors group"
                >
                  <td className="px-4 py-3 text-xs text-muted-foreground text-center">
                    {table.getState().pagination.pageIndex *
                      table.getState().pagination.pageSize +
                      idx +
                      1}
                  </td>
                  {row.getVisibleCells().map((cell) => (
                    <td
                      key={cell.id}
                      className="px-4 py-3 whitespace-nowrap text-foreground"
                    >
                      {flexRender(
                        cell.column.columnDef.cell,
                        cell.getContext()
                      )}
                    </td>
                  ))}
                  <td className="px-4 py-3">
                    <button
                      onClick={() => handleCopyRow(row.original)}
                      className="p-1 rounded-md opacity-0 group-hover:opacity-100 hover:bg-muted text-muted-foreground hover:text-foreground transition-all"
                      title="Copy row"
                      aria-label="Copy row data"
                    >
                      <Copy className="w-3.5 h-3.5" />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Pagination */}
      {rows.length > 0 && (
        <div className="px-5 py-3 border-t border-border flex flex-wrap items-center justify-between gap-3 text-sm text-muted-foreground">
          <div className="flex items-center gap-2">
            <span>Rows per page:</span>
            <select
              value={table.getState().pagination.pageSize}
              onChange={(e) => table.setPageSize(Number(e.target.value))}
              className="bg-muted/30 border border-border rounded-lg text-foreground px-2 py-1 text-xs outline-none focus:ring-1 focus:ring-primary/30"
              aria-label="Rows per page"
            >
              {[10, 25, 50, 100].map((size) => (
                <option key={size} value={size}>
                  {size}
                </option>
              ))}
            </select>
          </div>
          <div className="flex items-center gap-3">
            <span className="text-xs">
              Page {table.getState().pagination.pageIndex + 1} of{" "}
              {table.getPageCount()}
            </span>
            <div className="flex items-center gap-1">
              <button
                onClick={() => table.setPageIndex(0)}
                disabled={!table.getCanPreviousPage()}
                className="p-1.5 rounded-lg bg-muted/30 hover:bg-muted/50 disabled:opacity-30 transition-colors"
                aria-label="First page"
              >
                <ChevronsLeft className="w-4 h-4" />
              </button>
              <button
                onClick={() => table.previousPage()}
                disabled={!table.getCanPreviousPage()}
                className="p-1.5 rounded-lg bg-muted/30 hover:bg-muted/50 disabled:opacity-30 transition-colors"
                aria-label="Previous page"
              >
                <ChevronLeft className="w-4 h-4" />
              </button>
              <button
                onClick={() => table.nextPage()}
                disabled={!table.getCanNextPage()}
                className="p-1.5 rounded-lg bg-muted/30 hover:bg-muted/50 disabled:opacity-30 transition-colors"
                aria-label="Next page"
              >
                <ChevronRight className="w-4 h-4" />
              </button>
              <button
                onClick={() => table.setPageIndex(table.getPageCount() - 1)}
                disabled={!table.getCanNextPage()}
                className="p-1.5 rounded-lg bg-muted/30 hover:bg-muted/50 disabled:opacity-30 transition-colors"
                aria-label="Last page"
              >
                <ChevronsRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
