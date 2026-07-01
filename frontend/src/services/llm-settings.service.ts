import apiClient from '../lib/apiClient';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface LLMConfig {
  source: string;
  provider: string;
  model: string;
  ollama_base_url: string;
  api_key_set?: boolean;
}

export interface ConnectionTestResult {
  connected: boolean;
  message: string;
}

export interface ModelsResult {
  models: string[];
  provider: string;
}

export interface TestConnectionPayload {
  source: string;
  provider: string;
  model?: string;
  api_key?: string;
  ollama_base_url?: string;
}

export interface ListModelsPayload {
  source: string;
  provider: string;
  api_key?: string;
  ollama_base_url?: string;
}

// ---------------------------------------------------------------------------
// API
// ---------------------------------------------------------------------------

export const llmSettingsApi = {
  /** Retrieve the current active config from the backend. */
  getConfig: async (): Promise<LLMConfig> => {
    const response = await apiClient.get<LLMConfig>('/llm/config');
    return response.data;
  },

  /** Push a config update to the backend (api_key held in memory only). */
  updateConfig: async (config: Partial<LLMConfig> & { api_key?: string }): Promise<LLMConfig> => {
    const response = await apiClient.put<LLMConfig>('/llm/config', config);
    return response.data;
  },

  /** Test connectivity using the currently-active backend provider. */
  testConnectionActive: async (): Promise<ConnectionTestResult> => {
    const response = await apiClient.post<ConnectionTestResult>('/llm/test-connection');
    return response.data;
  },

  /** Ad-hoc connection probe — does NOT change the active config. */
  testConnection: async (payload: TestConnectionPayload): Promise<ConnectionTestResult> => {
    try {
      const response = await apiClient.post<ConnectionTestResult>(
        '/llm/test-connection/probe',
        payload,
      );
      return response.data;
    } catch (err: any) {
      const msg = err?.response?.data?.detail || err?.message || 'Connection test failed';
      return { connected: false, message: msg };
    }
  },

  /** List models for a specific provider without changing the active config. */
  listModels: async (payload: ListModelsPayload): Promise<ModelsResult> => {
    const response = await apiClient.post<ModelsResult>('/llm/models', payload);
    return response.data;
  },
};
