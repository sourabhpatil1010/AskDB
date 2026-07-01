/**
 * Zustand store for authentication state.
 *
 * The JWT token is persisted in localStorage under 'askdb-auth-token'.
 * The full user object is kept in memory (repopulated via /auth/me on refresh).
 *
 * Flow:
 *  1. User logs in → token saved to localStorage + user set in store
 *  2. Page refresh → AuthGuard calls fetchCurrentUser() → re-validates token with server
 *  3. Logout → token removed from localStorage + store cleared
 */
import { create } from 'zustand';
import { authApi } from '../services/auth.service';
import type { User } from '../types/auth';

const TOKEN_KEY = 'askdb-auth-token';

interface AuthState {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;

  // Actions
  login: (email: string, password: string) => Promise<void>;
  register: (fullName: string, email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  fetchCurrentUser: () => Promise<void>;
  clearError: () => void;
  setToken: (token: string) => void;
}

export const useAuthStore = create<AuthState>()((set, get) => ({
  user: null,
  token: localStorage.getItem(TOKEN_KEY),
  isAuthenticated: !!localStorage.getItem(TOKEN_KEY),
  isLoading: false,
  error: null,

  setToken: (token: string) => {
    localStorage.setItem(TOKEN_KEY, token);
    set({ token, isAuthenticated: true });
  },

  clearError: () => set({ error: null }),

  // ── Login ────────────────────────────────────────────────────────────────
  login: async (email: string, password: string) => {
    set({ isLoading: true, error: null });
    try {
      const tokenResponse = await authApi.login({ email, password });
      localStorage.setItem(TOKEN_KEY, tokenResponse.access_token);
      // Fetch user profile immediately after login
      const user = await authApi.getMe();
      set({
        token: tokenResponse.access_token,
        user,
        isAuthenticated: true,
        isLoading: false,
        error: null,
      });
    } catch (err: any) {
      const message = err.response?.data?.detail || 'Login failed. Please try again.';
      localStorage.removeItem(TOKEN_KEY);
      set({ isLoading: false, error: message, isAuthenticated: false, user: null, token: null });
      throw err;
    }
  },

  // ── Register ─────────────────────────────────────────────────────────────
  register: async (fullName: string, email: string, password: string) => {
    set({ isLoading: true, error: null });
    try {
      await authApi.register({ full_name: fullName, email, password });
      // Auto-login after successful registration
      await get().login(email, password);
    } catch (err: any) {
      const message = err.response?.data?.detail || 'Registration failed. Please try again.';
      set({ isLoading: false, error: message });
      throw err;
    }
  },

  // ── Logout ───────────────────────────────────────────────────────────────
  logout: async () => {
    set({ isLoading: true });
    try {
      await authApi.logout();
    } catch {
      // Ignore server errors on logout — we always clear client state
    } finally {
      localStorage.removeItem(TOKEN_KEY);
      set({ user: null, token: null, isAuthenticated: false, isLoading: false, error: null });
    }
  },

  // ── Re-hydrate on page refresh ───────────────────────────────────────────
  fetchCurrentUser: async () => {
    const token = localStorage.getItem(TOKEN_KEY);
    if (!token) {
      set({ isAuthenticated: false, user: null, isLoading: false });
      return;
    }
    set({ isLoading: true });
    try {
      const user = await authApi.getMe();
      set({ user, isAuthenticated: true, isLoading: false });
    } catch {
      // Token is invalid / expired — clear everything
      localStorage.removeItem(TOKEN_KEY);
      set({ user: null, token: null, isAuthenticated: false, isLoading: false });
    }
  },
}));
