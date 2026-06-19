import { useState, useMemo } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useQuery } from "@tanstack/react-query";
import {
  Database,
  Table2,
  Columns3,
  Key,
  Link2,
  Hash,
  Search,
  ChevronRight,
  ChevronDown,
  Loader2,
  AlertTriangle,
} from "lucide-react";
import { historyApi } from "@/services/history.service";

// We derive schema from history data + known tables.
// Since there's no dedicated schema endpoint, we show a representative schema.
interface TableSchema {
  name: string;
  columns: ColumnSchema[];
}

interface ColumnSchema {
  name: string;
  type: string;
  isPrimaryKey?: boolean;
  isForeignKey?: boolean;
  isNullable?: boolean;
  references?: string;
}

// Representative schema based on the enterprise HR database
const defaultSchema: TableSchema[] = [
  {
    name: "employees",
    columns: [
      { name: "id", type: "INTEGER", isPrimaryKey: true },
      { name: "first_name", type: "VARCHAR(100)" },
      { name: "last_name", type: "VARCHAR(100)" },
      { name: "email", type: "VARCHAR(255)" },
      { name: "salary", type: "DECIMAL(10,2)" },
      { name: "hire_date", type: "DATE" },
      { name: "department_id", type: "INTEGER", isForeignKey: true, references: "departments.id" },
      { name: "office_id", type: "INTEGER", isForeignKey: true, references: "offices.id" },
      { name: "created_at", type: "TIMESTAMP" },
    ],
  },
  {
    name: "departments",
    columns: [
      { name: "id", type: "INTEGER", isPrimaryKey: true },
      { name: "name", type: "VARCHAR(100)" },
      { name: "description", type: "TEXT", isNullable: true },
      { name: "created_at", type: "TIMESTAMP" },
    ],
  },
  {
    name: "offices",
    columns: [
      { name: "id", type: "INTEGER", isPrimaryKey: true },
      { name: "city", type: "VARCHAR(100)" },
      { name: "address", type: "TEXT" },
      { name: "country", type: "VARCHAR(100)" },
      { name: "created_at", type: "TIMESTAMP" },
    ],
  },
  {
    name: "projects",
    columns: [
      { name: "id", type: "INTEGER", isPrimaryKey: true },
      { name: "name", type: "VARCHAR(200)" },
      { name: "description", type: "TEXT", isNullable: true },
      { name: "start_date", type: "DATE" },
      { name: "end_date", type: "DATE", isNullable: true },
      { name: "status", type: "VARCHAR(50)" },
      { name: "created_at", type: "TIMESTAMP" },
    ],
  },
  {
    name: "employee_skills",
    columns: [
      { name: "id", type: "INTEGER", isPrimaryKey: true },
      { name: "employee_id", type: "INTEGER", isForeignKey: true, references: "employees.id" },
      { name: "skill", type: "VARCHAR(100)" },
      { name: "proficiency", type: "VARCHAR(50)" },
    ],
  },
  {
    name: "skills",
    columns: [
      { name: "id", type: "INTEGER", isPrimaryKey: true },
      { name: "name", type: "VARCHAR(100)" },
      { name: "category", type: "VARCHAR(100)" },
    ],
  },
  {
    name: "attendance",
    columns: [
      { name: "id", type: "INTEGER", isPrimaryKey: true },
      { name: "employee_id", type: "INTEGER", isForeignKey: true, references: "employees.id" },
      { name: "date", type: "DATE" },
      { name: "status", type: "VARCHAR(20)" },
      { name: "check_in", type: "TIME", isNullable: true },
      { name: "check_out", type: "TIME", isNullable: true },
    ],
  },
  {
    name: "employee_assignments",
    columns: [
      { name: "id", type: "INTEGER", isPrimaryKey: true },
      { name: "employee_id", type: "INTEGER", isForeignKey: true, references: "employees.id" },
      { name: "project_id", type: "INTEGER", isForeignKey: true, references: "projects.id" },
      { name: "role", type: "VARCHAR(100)" },
      { name: "assigned_date", type: "DATE" },
    ],
  },
  {
    name: "payroll",
    columns: [
      { name: "id", type: "INTEGER", isPrimaryKey: true },
      { name: "employee_id", type: "INTEGER", isForeignKey: true, references: "employees.id" },
      { name: "month", type: "DATE" },
      { name: "base_salary", type: "DECIMAL(10,2)" },
      { name: "bonus", type: "DECIMAL(10,2)", isNullable: true },
      { name: "deductions", type: "DECIMAL(10,2)", isNullable: true },
      { name: "net_salary", type: "DECIMAL(10,2)" },
    ],
  },
  {
    name: "search_history",
    columns: [
      { name: "id", type: "UUID", isPrimaryKey: true },
      { name: "user_id", type: "VARCHAR(100)" },
      { name: "natural_language", type: "TEXT" },
      { name: "structured_json", type: "JSONB", isNullable: true },
      { name: "generated_sql", type: "TEXT", isNullable: true },
      { name: "execution_time_ms", type: "INTEGER", isNullable: true },
      { name: "created_at", type: "TIMESTAMP" },
    ],
  },
];

export default function SchemaExplorerPage() {
  const [searchQuery, setSearchQuery] = useState("");
  const [expandedTables, setExpandedTables] = useState<Set<string>>(new Set());

  const schema = defaultSchema;

  const filteredSchema = useMemo(
    () =>
      schema.filter(
        (table) =>
          table.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
          table.columns.some((col) =>
            col.name.toLowerCase().includes(searchQuery.toLowerCase())
          )
      ),
    [schema, searchQuery]
  );

  const toggleTable = (tableName: string) => {
    setExpandedTables((prev) => {
      const next = new Set(prev);
      if (next.has(tableName)) {
        next.delete(tableName);
      } else {
        next.add(tableName);
      }
      return next;
    });
  };

  const expandAll = () => {
    setExpandedTables(new Set(filteredSchema.map((t) => t.name)));
  };

  const collapseAll = () => {
    setExpandedTables(new Set());
  };

  return (
    <div className="p-6 lg:p-8 max-w-[1200px] mx-auto">
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
      >
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-2xl font-bold text-foreground flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-emerald-500 to-teal-500 flex items-center justify-center shadow-lg">
              <Database className="w-5 h-5 text-white" />
            </div>
            Schema Explorer
          </h1>
          <p className="text-muted-foreground mt-2 text-sm">
            Browse your database structure, tables, columns, and relationships.
          </p>
        </div>

        {/* Search & Actions */}
        <div className="flex flex-wrap items-center gap-3 mb-6">
          <div className="relative flex-1 max-w-md">
            <Search className="w-4 h-4 absolute left-3.5 top-1/2 -translate-y-1/2 text-muted-foreground" />
            <input
              type="text"
              placeholder="Search tables and columns..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-10 pr-4 py-2.5 bg-card border border-border rounded-xl focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary/30 text-sm transition-all"
              aria-label="Search schema"
            />
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={expandAll}
              className="px-3 py-2 text-xs font-medium bg-card border border-border rounded-lg hover:bg-muted/50 transition-colors"
            >
              Expand All
            </button>
            <button
              onClick={collapseAll}
              className="px-3 py-2 text-xs font-medium bg-card border border-border rounded-lg hover:bg-muted/50 transition-colors"
            >
              Collapse All
            </button>
          </div>
          <span className="text-xs text-muted-foreground bg-muted/30 px-3 py-2 rounded-lg">
            {filteredSchema.length} tables
          </span>
        </div>

        {/* Tables */}
        <div className="space-y-3">
          {filteredSchema.map((table, idx) => {
            const isExpanded = expandedTables.has(table.name);
            const pkCount = table.columns.filter((c) => c.isPrimaryKey).length;
            const fkCount = table.columns.filter((c) => c.isForeignKey).length;

            return (
              <motion.div
                key={table.name}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: idx * 0.03 }}
                className="bg-card border border-border rounded-2xl overflow-hidden hover:shadow-md hover:border-primary/10 transition-all duration-300"
              >
                <button
                  onClick={() => toggleTable(table.name)}
                  className="w-full flex items-center gap-3 px-5 py-4 text-left"
                  aria-expanded={isExpanded}
                  aria-label={`${isExpanded ? "Collapse" : "Expand"} table ${table.name}`}
                >
                  {isExpanded ? (
                    <ChevronDown className="w-4 h-4 text-muted-foreground shrink-0" />
                  ) : (
                    <ChevronRight className="w-4 h-4 text-muted-foreground shrink-0" />
                  )}
                  <Table2 className="w-5 h-5 text-primary shrink-0" />
                  <span className="font-semibold text-foreground">{table.name}</span>
                  <div className="flex items-center gap-2 ml-auto">
                    <span className="text-xs text-muted-foreground bg-muted/30 px-2 py-0.5 rounded-md">
                      {table.columns.length} cols
                    </span>
                    {pkCount > 0 && (
                      <span className="text-xs text-amber-500 bg-amber-500/10 px-2 py-0.5 rounded-md flex items-center gap-1">
                        <Key className="w-3 h-3" />
                        {pkCount} PK
                      </span>
                    )}
                    {fkCount > 0 && (
                      <span className="text-xs text-blue-500 bg-blue-500/10 px-2 py-0.5 rounded-md flex items-center gap-1">
                        <Link2 className="w-3 h-3" />
                        {fkCount} FK
                      </span>
                    )}
                  </div>
                </button>

                <AnimatePresence>
                  {isExpanded && (
                    <motion.div
                      initial={{ height: 0, opacity: 0 }}
                      animate={{ height: "auto", opacity: 1 }}
                      exit={{ height: 0, opacity: 0 }}
                      transition={{ duration: 0.2 }}
                      className="overflow-hidden"
                    >
                      <div className="border-t border-border">
                        <table className="w-full text-sm">
                          <thead>
                            <tr className="text-xs text-muted-foreground bg-muted/20">
                              <th className="px-5 py-2.5 text-left font-medium">Column</th>
                              <th className="px-5 py-2.5 text-left font-medium">Type</th>
                              <th className="px-5 py-2.5 text-left font-medium">Constraints</th>
                              <th className="px-5 py-2.5 text-left font-medium">References</th>
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-border">
                            {table.columns.map((col) => (
                              <tr
                                key={col.name}
                                className="hover:bg-muted/10 transition-colors"
                              >
                                <td className="px-5 py-2.5 font-medium text-foreground flex items-center gap-2">
                                  {col.isPrimaryKey && (
                                    <Key className="w-3.5 h-3.5 text-amber-500" />
                                  )}
                                  {col.isForeignKey && !col.isPrimaryKey && (
                                    <Link2 className="w-3.5 h-3.5 text-blue-500" />
                                  )}
                                  {!col.isPrimaryKey && !col.isForeignKey && (
                                    <Columns3 className="w-3.5 h-3.5 text-muted-foreground/50" />
                                  )}
                                  {col.name}
                                </td>
                                <td className="px-5 py-2.5">
                                  <span className="text-xs font-mono bg-muted/30 px-2 py-0.5 rounded text-muted-foreground">
                                    {col.type}
                                  </span>
                                </td>
                                <td className="px-5 py-2.5">
                                  <div className="flex items-center gap-1">
                                    {col.isPrimaryKey && (
                                      <span className="text-xs text-amber-500 bg-amber-500/10 px-1.5 py-0.5 rounded">
                                        PK
                                      </span>
                                    )}
                                    {col.isForeignKey && (
                                      <span className="text-xs text-blue-500 bg-blue-500/10 px-1.5 py-0.5 rounded">
                                        FK
                                      </span>
                                    )}
                                    {col.isNullable && (
                                      <span className="text-xs text-muted-foreground/70">
                                        nullable
                                      </span>
                                    )}
                                    {!col.isPrimaryKey &&
                                      !col.isForeignKey &&
                                      !col.isNullable && (
                                        <span className="text-xs text-emerald-500">
                                          NOT NULL
                                        </span>
                                      )}
                                  </div>
                                </td>
                                <td className="px-5 py-2.5 text-xs text-muted-foreground">
                                  {col.references || "—"}
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </motion.div>
            );
          })}
        </div>
      </motion.div>
    </div>
  );
}
