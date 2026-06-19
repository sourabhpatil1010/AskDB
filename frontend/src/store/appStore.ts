import { create } from 'zustand';
import { persist } from 'zustand/middleware';

export interface SavedQuery {
  id: string;
  query: string;
  sql?: string;
  createdAt: string;
  isFavorite: boolean;
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
    llmModel: string;
    language: string;
  };
  updateSettings: (settings: Partial<AppStore['settings']>) => void;
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
        llmModel: 'llama-3.3-70b-versatile',
        language: 'en',
      },
      updateSettings: (settings) =>
        set((state) => ({
          settings: { ...state.settings, ...settings },
        })),
    }),
    {
      name: 'askdb-app-store',
    }
  )
);
