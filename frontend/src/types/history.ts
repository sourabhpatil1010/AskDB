export interface SearchHistory {
  id: string;
  user_id: string;
  natural_language: string;
  structured_json?: any;
  generated_sql?: string;
  execution_time_ms?: number;
  status: string;
  error_message?: string;
  row_count?: number;
  created_at: string;
}
