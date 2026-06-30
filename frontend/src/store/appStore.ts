import { create } from 'zustand';
import { persist } from 'zustand/middleware';

export interface SavedQuery {
  id: string;
  query: string;
  sql?: string;
  createdAt: string;
  isFavorite: boolean;
}

export type AISource = 'cloud' | 'local';

export type CloudProvider = 'groq' | 'openai' | 'gemini' | 'anthropic' | 'openrouter';

export type AnyProvider = CloudProvider | 'ollama';

export interface LLMSettings {
  aiSource: AISource;
  provider: AnyProvider;
  model: string;
  ollamaBaseUrl: string;
  /** Runtime API key — stored in sessionStorage (or localStorage if rememberKey=true).
   *  Never sent to PostgreSQL. */
  apiKey: string;
  /** Whether to persist the API key in localStorage between sessions. */
  rememberKey: boolean;
}

interface AppStore {
  sidebarCollapsed: boolean;
  toggleSidebar: () => void;
  setSidebarCollapsed: (collapsed: boolean) => void;
  savedQueries: SavedQuery[];
  addSavedQuery: (query: Omit<SavedQuery, 'id' | 'createdAt' | 'isFavorite'>) => void;
  removeSavedQuery: (id: string) => void;
  toggleFavoriteQuery: (id: string) => void;
  updateSavedQuery: (id: string, updates: Partial<SavedQuery>) => void;
  settings: {
    apiUrl: string;
    language: string;
  };
  updateSettings: (settings: Partial<AppStore['settings']>) => void;
  llmSettings: LLMSettings;
  updateLLMSettings: (settings: Partial<LLMSettings>) => void;
}

export const useAppStore = create<AppStore>()(
  persist(
    (set) => ({
      sidebarCollapsed: false,
      toggleSidebar: () => set((state) => ({ sidebarCollapsed: !state.sidebarCollapsed })),
      setSidebarCollapsed: (collapsed) => set({ sidebarCollapsed: collapsed }),
      savedQueries: [],
      addSavedQuery: (query) =>
        set((state) => ({
          savedQueries: [
            {
              ...query,
              id: crypto.randomUUID(),
              createdAt: new Date().toISOString(),
              isFavorite: false,
            },
            ...state.savedQueries,
          ],
        })),
      removeSavedQuery: (id) =>
        set((state) => ({
          savedQueries: state.savedQueries.filter((q) => q.id !== id),
        })),
      toggleFavoriteQuery: (id) =>
        set((state) => ({
          savedQueries: state.savedQueries.map((q) =>
            q.id === id ? { ...q, isFavorite: !q.isFavorite } : q
          ),
        })),
      updateSavedQuery: (id, updates) =>
        set((state) => ({
          savedQueries: state.savedQueries.map((q) =>
            q.id === id ? { ...q, ...updates } : q
          ),
        })),
      settings: {
        apiUrl: import.meta.env.VITE_API_URL || 'http://localhost:8000',
        language: 'en',
      },
      updateSettings: (settings) =>
        set((state) => ({
          settings: { ...state.settings, ...settings },
        })),
      llmSettings: {
        aiSource: 'cloud',
        provider: 'groq',
        model: 'qwen/qwen3-32b',
        ollamaBaseUrl: 'http://localhost:11434',
        apiKey: '',
        rememberKey: false,
      },
      updateLLMSettings: (llmSettings) =>
        set((state) => ({
          llmSettings: { ...state.llmSettings, ...llmSettings },
        })),
    }),
    {
      name: 'askdb-app-store',
      // Never persist the API key in localStorage unless rememberKey is true.
      // We achieve this by stripping the apiKey from the persisted object
      // when rememberKey is false.
      partialize: (state) => ({
        ...state,
        llmSettings: {
          ...state.llmSettings,
          // Only persist the API key when user opted in
          apiKey: state.llmSettings.rememberKey ? state.llmSettings.apiKey : '',
        },
      }),
    }
  )
);
