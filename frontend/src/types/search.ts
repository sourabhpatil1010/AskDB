export interface SearchRequest {
  query: string;
}

export interface SearchResponse {
  success: boolean;
  question?: string;
  structured_json?: any;
  generated_sql?: string;
  parameters?: Record<string, any>;
  execution_time_ms?: number;
  row_count?: number;
  columns?: string[];
  rows?: any[];
  error?: string;
}
