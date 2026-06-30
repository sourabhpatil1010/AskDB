import { BarChart3 } from "lucide-react";

interface EmptyChartStateProps {
  message?: string;
}

export function EmptyChartState({
  message = "No suitable visualization available for this dataset.",
}: EmptyChartStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-16 px-8 text-center">
      <div className="w-16 h-16 rounded-2xl bg-muted/50 border border-border flex items-center justify-center mb-4">
        <BarChart3 className="w-8 h-8 text-muted-foreground/40" />
      </div>
      <p className="text-base font-medium text-foreground mb-1">
        No Visualization Available
      </p>
      <p className="text-sm text-muted-foreground max-w-sm">{message}</p>
      <p className="text-xs text-muted-foreground/60 mt-3">
        Try a query that returns numeric data with categories or dates.
      </p>
    </div>
  );
}
